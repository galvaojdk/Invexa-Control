import os
from fastapi import APIRouter, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.dependencies import get_db, login_required
from app.models.user import User
from app.models.ticket import SupportTicket, TicketMessage

router = APIRouter(prefix="/support", tags=["support"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def help_center(request: Request, db: Session = Depends(get_db), current_user: User = Depends(login_required)):
    tickets = db.query(SupportTicket).filter(SupportTicket.user_id == current_user.id).order_by(desc(SupportTicket.created_at)).all()
    return templates.TemplateResponse("support_index.html", {
        "request": request,
        "user": current_user,
        "tickets": tickets
    })

@router.post("/new")
async def create_ticket(
    request: Request,
    subject: str = Form(...),
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(login_required)
):
    # Create the ticket
    new_ticket = SupportTicket(
        user_id=current_user.id,
        company_id=current_user.company_id,
        subject=subject,
        status="open"
    )
    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    # Add the initial message
    new_message = TicketMessage(
        ticket_id=new_ticket.id,
        sender_id=current_user.id,
        message=message
    )
    db.add(new_message)
    db.commit()

    return RedirectResponse(f"/support/{new_ticket.id}", status_code=status.HTTP_302_FOUND)

@router.get("/{ticket_id}", response_class=HTMLResponse)
async def view_ticket(ticket_id: int, request: Request, db: Session = Depends(get_db), current_user: User = Depends(login_required)):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id, SupportTicket.user_id == current_user.id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return templates.TemplateResponse("support_view.html", {
        "request": request,
        "user": current_user,
        "ticket": ticket
    })

@router.post("/{ticket_id}/reply")
async def reply_ticket(
    ticket_id: int,
    request: Request,
    message: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(login_required)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id, SupportTicket.user_id == current_user.id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status == "closed":
        # Maybe handle gracefully depending on requirement
        pass
    else:
        new_message = TicketMessage(
            ticket_id=ticket.id,
            sender_id=current_user.id,
            message=message
        )
        db.add(new_message)
        
        # Optionally, mark ticket as 'open' again if it was 'in_progress' and user answers
        # Here we just leave it as is or change to 'open' if it was answered by admin
        ticket.status = "open"

        db.commit()

    return RedirectResponse(f"/support/{ticket_id}", status_code=status.HTTP_302_FOUND)
