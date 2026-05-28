"""
图库管理路由

提供图片上传、列表查询、删除等功能。
"""

import os
import shutil
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.response import list_success, success

router = APIRouter(prefix='/gallery', tags=['图库管理'])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads', 'gallery')
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.get('/images')
def list_images(db: Session = Depends(get_db)):
    """获取所有图片列表"""
    images = db.query(models.GalleryImage).order_by(models.GalleryImage.created_at.desc()).all()
    return list_success([schemas.GalleryImageResponse.model_validate(img) for img in images])


@router.post('/upload', dependencies=[Depends(get_current_user)])
def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """上传单张图片"""
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail='仅支持 jpeg/png/gif/webp 格式的图片')

    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail='单张图片大小不能超过 10MB')

    ext = os.path.splitext(file.filename)[1].lower()
    if not ext:
        ext = '.png'
    store_name = f'{uuid.uuid4().hex}{ext}'
    store_path = os.path.join(UPLOAD_DIR, store_name)

    with open(store_path, 'wb') as f:
        f.write(content)

    db_image = models.GalleryImage(
        filename=store_name,
        original_name=file.filename,
        file_size=len(content),
        mime_type=file.content_type,
        url_path=f'/uploads/gallery/{store_name}',
    )
    db.add(db_image)
    db.commit()
    db.refresh(db_image)

    return success(schemas.GalleryImageResponse.model_validate(db_image))


@router.delete('/images/{image_id}', dependencies=[Depends(get_current_user)])
def delete_image(image_id: int, db: Session = Depends(get_db)):
    """删除指定图片"""
    image = db.query(models.GalleryImage).filter(models.GalleryImage.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail='图片不存在')

    store_path = os.path.join(UPLOAD_DIR, image.filename)
    if os.path.exists(store_path):
        os.remove(store_path)

    db.delete(image)
    db.commit()
    return success()
