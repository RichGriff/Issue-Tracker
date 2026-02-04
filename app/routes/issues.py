import uuid

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from app.schemas import IssueCreate, IssueResponse, IssueUpdate
from app.database.config import get_db
from app.database import models
from app.tasks.issues import notify_issue_creation

router = APIRouter(prefix="/api/v1/issues", tags=["issues"])


@router.get("/", response_model=list[IssueResponse])
def list_issues(db: Session = Depends(get_db)):
    """List all issues from the database."""
    issues = db.query(models.Issue).all()
    return issues


@router.get("/{issue_id}", response_model=IssueResponse, status_code=status.HTTP_200_OK)
def get_issue(issue_id: str, db: Session = Depends(get_db)):
    """Get issue by ID"""
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        )

    return issue


@router.post("/", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def create_issue(
    payload: IssueCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create new issue"""
    new_issue = models.Issue(
        id=str(uuid.uuid4()),
        title=payload.title,
        description=payload.description,
        priority=payload.priority.value,
        status="open",
    )
    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)

    """Run Background Tasks - Notify on creation"""
    background_tasks.add_task(
        notify_issue_creation, 
        issue = new_issue
    )

    return new_issue


@router.put("/{issue_id}", response_model=IssueResponse, status_code=status.HTTP_200_OK)
def update_issue(issue_id: str, payload: IssueUpdate, db: Session = Depends(get_db)):
    """Update issue by ID"""
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        )

    if payload.title is not None:
        issue.title = payload.title
    if payload.description is not None:
        issue.description = payload.description
    if payload.priority is not None:
        issue.priority = payload.priority.value
    if payload.status is not None:
        issue.status = payload.status.value

    db.commit()
    db.refresh(issue)
    return issue


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue(issue_id: str, db: Session = Depends(get_db)):
    """Delete issue by ID"""
    issue = db.query(models.Issue).filter(models.Issue.id == issue_id).first()

    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found"
        )

    db.delete(issue)
    db.commit()
