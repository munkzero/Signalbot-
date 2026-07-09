    def _polling_loop(self):
        """
        Polling loop: periodically calls ``signal-cli receive`` to fetch
        pending messages. Runs every 5 seconds in a background thread.
        """
        poll_interval = 5

        print("DEBUG: Entering polling loop (signal-cli receive mode)")

        while self.listening:
            try:
                # Use plain receive (no --json) with short timeout
                result = subprocess.run(
                    ["signal-cli", "-a", self.phone_number, "receive", "--timeout", "1"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    # Parse the text output from signal-cli receive
                    output = result.stdout.strip()
                    print(f"DEBUG: Received signal-cli output")
                    
                    # Parse envelope lines
                    lines = output.split('\n')
                    for i, line in enumerate(lines):
                        line = line.strip()
                        
                        # Look for "Envelope from:" lines which indicate a new message
                        if line.startswith('Envelope from:'):
                            # Parse sender from envelope
                            # Example: Envelope from: "Satoshi" +64274268090 (device: 1) to +64274268090
                            try:
                                # Extract phone number (looks for pattern like +64274268090)
                                import re
                                phone_match = re.search(r'\+\d+', line)
                                if phone_match:
                                    sender = phone_match.group(0)
                                    
                                    # Look ahead for the message body in subsequent lines
                                    message_text = ""
                                    if i + 1 < len(lines):
                                        # Next line might have timestamp, skip it
                                        if "Timestamp:" in lines[i + 1]:
                                            # Message text is usually 2-3 lines after envelope
                                            if i + 3 < len(lines):
                                                message_text = lines[i + 3].strip()
                                        else:
                                            message_text = lines[i + 1].strip()
                                    
                                    if sender and message_text and sender != self.phone_number:
                                        print(f"✅ Parsed message from {sender}: {message_text[:50]}")
                                        
                                        # Create and process message
                                        message = {
                                            'sender': sender,
                                            'text': message_text,
                                            'timestamp': int(time.time() * 1000),
                                            'is_group': False,
                                            'group_id': None,
                                            'recipient_identity': self.phone_number
                                        }
                                        
                                        # Process buyer commands
                                        if self.buyer_handler and message_text:
                                            try:
                                                print(f"DEBUG: Processing message from {sender}")
                                                self.buyer_handler.handle_buyer_message(sender, message_text, self.phone_number)
                                            except Exception as e:
                                                print(f"ERROR: Error in buyer handler: {e}")
                                        
                                        # Call registered callbacks
                                        for callback in self.message_callbacks:
                                            try:
                                                callback(message)
                                            except Exception as e:
                                                print(f"ERROR: Error in message callback: {e}")
                            except Exception as e:
                                print(f"DEBUG: Error parsing envelope: {e}")
                                
            except FileNotFoundError:
                print("ERROR: signal-cli not found; polling mode unavailable")
                break
            except Exception as exc:
                print(f"WARNING: Polling error: {exc}")

            time.sleep(poll_interval)
