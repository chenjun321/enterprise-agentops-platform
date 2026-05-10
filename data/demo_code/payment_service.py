class PaymentService:
    def handle_payment_callback(self, payload):
        trace_id = payload["trace_id"]
        if payload.get("status") == "success":
            updated = self.update_order_status(payload["order_no"], "paid")
            if not updated:
                self.log_error(trace_id, "PAYMENT_CALLBACK_TIMEOUT payment callback timeout")
                return {"ok": False, "error": "PAYMENT_CALLBACK_TIMEOUT"}
        return {"ok": True}

    def update_order_status(self, order_no, status):
        if not order_no:
            return False
        return True

    def log_error(self, trace_id, message):
        print(f"{trace_id}: {message}")


def trigger_payment_reconcile_job(order_no):
    return {"job": "payment_reconcile_job", "order_no": order_no, "status": "queued"}

