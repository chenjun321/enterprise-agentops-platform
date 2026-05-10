class OrderService:
    def mark_paid(self, order_no):
        return {"order_no": order_no, "status": "paid"}

    def keep_pending_until_callback(self, order_no):
        return {"order_no": order_no, "status": "pending"}

