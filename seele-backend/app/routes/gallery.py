"""
图库管理路由

图片统一存储在七牛云 Kodo，前端通过 CDN 域名访问。
"""

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from qiniu import Auth, put_data, BucketManager, build_batch_delete
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.response import list_success, success

router = APIRouter(prefix='/gallery', tags=['图库管理'])

ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
PREFIX = 'photo/'


def _get_qiniu_auth():
    settings = get_settings()
    if not settings.qiniu_access_key or not settings.qiniu_secret_key:
        raise HTTPException(status_code=500, detail='七牛云配置未就绪')
    return Auth(settings.qiniu_access_key, settings.qiniu_secret_key)


def _get_bucket():
    settings = get_settings()
    return settings.qiniu_bucket


def _get_cdn_url(key):
    settings = get_settings()
    domain = settings.qiniu_domain.rstrip('/')
    return f'{domain}/{key}'


@router.get('/images')
def list_images(db: Session = Depends(get_db)):
    """获取所有图片列表（以数据库记录为准，同步七牛云元数据）"""
    images = db.query(models.GalleryImage).order_by(models.GalleryImage.created_at.desc()).all()
    return list_success([schemas.GalleryImageResponse.model_validate(img) for img in images])


@router.post('/upload', dependencies=[Depends(get_current_user)])
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传单张图片到七牛云"""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail='仅支持 jpeg/png/gif/webp 格式的图片')

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail='单张图片大小不能超过 10MB')

    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        ext = '.png'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    rand = uuid.uuid4().hex[:6]
    key = f'{PREFIX}{ts}_{rand}{ext}'

    q = _get_qiniu_auth()
    token = q.upload_token(_get_bucket(), key, 3600)
    ret, info = put_data(token, key, content)
    if not ret or info.status_code != 200:
        raise HTTPException(status_code=500, detail=f'七牛云上传失败: {info}')

    db_image = models.GalleryImage(
        filename=key,
        original_name=file.filename,
        file_size=len(content),
        mime_type=file.content_type,
        url_path=_get_cdn_url(key),
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return success(schemas.GalleryImageResponse.model_validate(db_image))


@router.delete('/images/{image_id}', dependencies=[Depends(get_current_user)])
def delete_image(image_id: int, db: Session = Depends(get_db)):
    """删除指定图片（七牛云 + 数据库）"""
    image = db.query(models.GalleryImage).filter(models.GalleryImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail='图片不存在')

    q = _get_qiniu_auth()
    bucket = BucketManager(q)
    ret, info = bucket.delete(_get_bucket(), image.filename)
    if ret is not None or info.status_code not in (200, 612):
        # 612 表示文件已不存在，视为成功
        if info.status_code != 612:
            raise HTTPException(status_code=500, detail=f'七牛云删除失败: {info}')

    db.delete(image)
    db.commit()
    return success()


@router.post('/sync-qiniu', dependencies=[Depends(get_current_user)])
def sync_from_qiniu(db: Session = Depends(get_db)):
    """从七牛云同步文件列表到数据库（清理本地已不存在的记录，补充新增文件）"""
    q = _get_qiniu_auth()
    bucket = BucketManager(q)
    marker = ''
    qiniu_keys = set()

    while True:
        ret, eof, info = bucket.list(_get_bucket(), prefix=PREFIX, marker=marker, limit=1000)
        if not ret or 'items' not in ret:
            break
        for item in ret['items']:
            qiniu_keys.add(item['key'])
        if eof:
            break
        marker = ret.get('marker', '')
        if not marker:
            break

    # 清理数据库中已不在七牛云的记录
    db_images = db.query(models.GalleryImage).all()
    for img in db_images:
        if img.filename not in qiniu_keys:
            db.delete(img)

    # 补充七牛云中有但数据库没有的记录
    db_keys = {img.filename for img in db_images}
    for key in qiniu_keys:
        if key not in db_keys:
            stat_ret, stat_info = bucket.stat(_get_bucket(), key)
            if stat_ret:
                db_image = models.GalleryImage(
                    filename=key,
                    original_name=os.path.basename(key),
                    file_size=stat_ret.get('fsize', 0),
                    mime_type=stat_ret.get('mimeType', 'image/jpeg'),
                    url_path=_get_cdn_url(key),
                )
                db.add(db_image)

    db.commit()
    return list_success([schemas.GalleryImageResponse.model_validate(img) for img in db.query(models.GalleryImage).order_by(models.GalleryImage.created_at.desc()).all()])
