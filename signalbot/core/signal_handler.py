    def send_message_native(self, recipient: str, message: str = None, attachments: List[str] = None) -> bool:
        """
        Ultra-fast native send using signal-cli command directly.
        This bypasses daemon JSON-RPC for speed.

        Speed: 5-10 seconds (vs 30-60s with daemon JSON-RPC)

        Args:
            recipient: Phone number
            message: Text message
            attachments: List of file paths

        Returns:
            True if command executed successfully, False on error
        """
        import subprocess

        cmd = ['signal-cli', '-a', self.phone_number, 'send']

        if message:
            cmd.extend(['-m', message])

        cmd.append(recipient)

        if attachments:
            for attachment in attachments:
                if os.path.exists(attachment):
                    cmd.extend(['--attachment', attachment])
                else:
                    logger.warning(f"Attachment not found, skipping: {attachment}")

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
                check=False
            )

            if result.returncode == 0:
                logger.debug(f"✅ Native send to {recipient} completed")
                self._record_live_message(
                    recipient,
                    message or ("[Attachment]" if attachments else ""),
                    int(time.time() * 1000),
                    is_outgoing=True,
                )
                return True
            else:
                error = result.stderr.decode('utf-8', errors='ignore')
                error_msg = error.strip()
                print(f"⚠️ Native send FAILED with returncode {result.returncode}")
                print(f"   Error: {error_msg}")
                print(f"   Command: signal-cli -a <phone> send -m '<message>' {recipient}")
                logger.warning(f"⚠️ Native send failed with returncode {result.returncode}: {error_msg[:250]}")
                # Return False on actual error
                return False

        except subprocess.TimeoutExpired:
            print(f"❌ Native send timeout (30s) to {recipient}")
            logger.error(f"❌ Native send timeout (30s) to {recipient}")
            return False
        except Exception as e:
            print(f"❌ Native send exception: {e}")
            logger.error(f"❌ Native send failed: {e}")
            return False
