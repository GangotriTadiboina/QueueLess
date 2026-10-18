from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.database.models import Service,User
from app.schemas.service import ServiceIn, ServiceOut
from app.core.security import get_current_user

router=APIRouter(
    prefix="/services",
    tags=["Services"]
)

@router.post("/",response_model=ServiceOut)
def create_service(service: ServiceIn,db: Session=Depends(get_db), current_user=Depends(get_current_user)):
    existing_service=db.query(Service).filter(Service.name==service.name).first()
    if existing_service:
        raise HTTPException(
            status_code=400,
            detail="Service already exists"
        )
    new_service=Service(
        name=service.name,
        description=service.description,
        user_id=current_user.id
    )
    db.add(new_service)
    db.commit()
    db.refresh(new_service)
    return new_service

@router.get("/",response_model=list[ServiceOut])
def get_services(db: Session=Depends(get_db)):
    services=db.query(Service).all()
    return services

@router.get("/{service_id}",response_model=ServiceOut)
def get_service(service_id:int,db:Session=Depends(get_db)):
    service=db.query(Service).filter(Service.id==service_id).first()
    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service not found"
        )
    return service

