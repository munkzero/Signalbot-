        # ===== SEND INSTRUCTIONS FOOTER =====
        instructions = """✨ CATALOG COMPLETE ✨

📋 HOW TO ORDER:
Reply with: order #1 qty 2
(replace #1 with product number, 2 with quantity)

💳 AFTER YOU ORDER:
• You get payment address & QR code
• Send XMR amount to address
• We'll ship when paid

❓ CHECK ORDER STATUS:
Reply: "status" to see your order info

Need help? Reply: help"""
        try:
            print(f"\n📝 Sending order instructions...")
            self.signal_handler.send_message_native(
                recipient=buyer_signal_id,
                message=instructions.strip()
            )
            print(f"✅ Instructions sent\n")
        except Exception as e:
            print(f"⚠️ Instructions send failed: {e}\n")
