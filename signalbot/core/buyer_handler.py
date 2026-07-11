        failed_count = total_products - sent_count

        # ===== SEND INSTRUCTIONS FOOTER WITH COMPREHENSIVE ERROR HANDLING =====
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
        
        sent_footer = False
        footer_error = None
        
        print(f"\n📝 Attempting to send order instructions (footer)...")
        
        # Attempt #1: Direct send_message_native with error details
        try:
            print(f"   [Attempt 1] Using send_message_native()...")
            result = self.signal_handler.send_message_native(
                recipient=buyer_signal_id,
                message=instructions.strip()
            )
            if result:
                print(f"✅ Footer sent successfully (send_message_native)\n")
                sent_footer = True
            else:
                footer_error = "send_message_native() returned False/None"
                print(f"   [Attempt 1 FAILED] {footer_error}\n")
        except Exception as e1:
            footer_error = str(e1)
            print(f"   [Attempt 1 FAILED] Exception: {e1}\n")
        
        # Attempt #2: Try again with explicit recipient handling
        if not sent_footer:
            try:
                print(f"   [Attempt 2] Retry with explicit recipient: {buyer_signal_id}")
                # Ensure recipient format is correct
                recipient = buyer_signal_id if buyer_signal_id.startswith(('+', '@')) else buyer_signal_id
                result = self.signal_handler.send_message_native(
                    recipient=recipient,
                    message=instructions.strip()
                )
                if result:
                    print(f"✅ Footer sent successfully (retry with explicit recipient)\n")
                    sent_footer = True
                else:
                    print(f"   [Attempt 2 FAILED] send_message_native() returned False/None\n")
            except Exception as e2:
                print(f"   [Attempt 2 FAILED] Exception: {e2}\n")
        
        # Attempt #3: Try sending in smaller chunks (in case message size is the issue)
        if not sent_footer:
            try:
                print(f"   [Attempt 3] Sending in two chunks (might be too long)...")
                
                chunk1 = "✨ CATALOG COMPLETE ✨\n\n📋 HOW TO ORDER:\nReply with: order #1 qty 2"
                chunk2 = "💳 AFTER YOU ORDER:\n• You get payment address & QR code\n• Send XMR amount to address\n• We'll ship when paid\n\n❓ CHECK ORDER STATUS:\nReply: \"status\"\n\nNeed help? Reply: help"
                
                result1 = self.signal_handler.send_message_native(
                    recipient=buyer_signal_id,
                    message=chunk1
                )
                time.sleep(0.5)  # Small delay between chunks
                result2 = self.signal_handler.send_message_native(
                    recipient=buyer_signal_id,
                    message=chunk2
                )
                
                if result1 and result2:
                    print(f"✅ Footer sent successfully (as two chunks)\n")
                    sent_footer = True
                else:
                    print(f"   [Attempt 3 FAILED] One or both chunks failed\n")
            except Exception as e3:
                print(f"   [Attempt 3 FAILED] Exception: {e3}\n")
        
        # Attempt #4: Emergency fallback - just the essentials
        if not sent_footer:
            try:
                print(f"   [Attempt 4] Emergency fallback - essentials only...")
                minimal = "✨ CATALOG COMPLETE ✨\nReply: order #1 qty 2\nReply: status\nReply: help"
                result = self.signal_handler.send_message_native(
                    recipient=buyer_signal_id,
                    message=minimal
                )
                if result:
                    print(f"✅ Footer sent successfully (emergency fallback)\n")
                    sent_footer = True
                else:
                    print(f"   [Attempt 4 FAILED] Emergency fallback also failed\n")
            except Exception as e4:
                print(f"   [Attempt 4 FAILED] Exception: {e4}\n")

        # Summary report
        print(f"\n{'='*60}")
        print(f"📊 CATALOG SEND COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Products sent: {sent_count}/{total_products}")
        if failed_count:
            print(f"⚠️ Failed: {failed_count}")
        print(f"✅ Footer sent: {'YES' if sent_footer else 'NO - ALL ATTEMPTS FAILED'}")
        if not sent_footer and footer_error:
            print(f"❌ Last error: {footer_error}")
        print(f"{'='*60}\n")
