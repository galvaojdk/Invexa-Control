from sqlalchemy.orm import Session
from datetime import datetime
from app.models.inventory import Product, Movement, MovementType, AuditLog
from app.models.user import User

class InventoryService:
    @staticmethod
    def register_stock_movement(
        db: Session,
        product_id: int,
        quantity: float,
        mov_type: MovementType,
        user_id: int,
        company_id: int,
        reason: str = None,
        sector: str = None
    ) -> Movement:
        """
        Centrally handles stock updates, movement records, and audit logs.
        Refined to ensure atomic operation and consistent state.
        """
        product = db.query(Product).filter(Product.id == product_id, Product.company_id == company_id).first()
        if not product:
            raise ValueError("Produto não encontrado ou acesso negado")

        # Update Stock
        if mov_type == MovementType.IN:
            product.current_stock += quantity
        else:
            # Allow negative stock as per user request (stock managed externally)
            product.current_stock -= quantity
        
        db.add(product)

        # Create Movement
        movement = Movement(
            product_id=product_id,
            quantity=quantity,
            type=mov_type,
            reason=reason,
            timestamp=datetime.now(),
            user_id=user_id,
            company_id=company_id,
            sector=sector
        )
        db.add(movement)
        db.flush() # Get movement ID

        # Create Audit Log
        action_type = "ENTRADA_ESTOQUE" if mov_type == MovementType.IN else "SAIDA_ESTOQUE"
        audit = AuditLog(
            user_id=user_id,
            company_id=company_id,
            action=action_type,
            resource_type="movement",
            resource_id=movement.id,
            description=f"{mov_type.value.capitalize()} de {quantity} unidades do produto '{product.name}' (SKU: {product.sku}). Setor: {sector or '-'}. Motivo: {reason or '-'}"
        )
        db.add(audit)
        
        # Note: We don't db.commit() here to allow this to be part of a larger transaction
        return movement

    @staticmethod
    def bulk_import_stock(db: Session, user: User, items: list):
        """
        Example for future refactoring of CSV/XML imports to use this service.
        """
        for item in items:
            InventoryService.register_stock_movement(
                db=db,
                product_id=item['product_id'],
                quantity=item['quantity'],
                mov_type=item['type'],
                user_id=user.id,
                company_id=user.company_id,
                reason=item.get('reason'),
                sector=item.get('sector')
            )
