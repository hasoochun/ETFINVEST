"""
Add missing methods to bot_controller.py
"""

file_path = r'c:\Users\user\.gemini\antigravity\scratch\open-trading-api\infinite_buying_bot\api\bot_controller.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add methods before the last line (which should be the end of the class or file)
methods_to_add = '''
    def set_dip_buy_mode(self, mode: str):
        """
        Set dip buying mode
        
        Args:
            mode: 'daily' or 'accelerated'
        """
        if mode not in ['daily', 'accelerated']:
            raise ValueError("Mode must be 'daily' or 'accelerated'")
        self.dip_buy_mode = mode
        logger.info(f"Dip buy mode changed to: {mode}")
    
    def get_next_dip_buy_time(self) -> str:
        """
        Calculate next dip buy time based on mode
        
        Returns:
            String describing next buy time
        """
        from datetime import timedelta
        import pytz
        
        if self.dip_buy_mode == 'daily':
            # Next market close - 5 minutes (15:55 ET)
            et = pytz.timezone('US/Eastern')
            now_et = datetime.now(et)
            
            # Create buy window time (15:55)
            buy_time = now_et.replace(hour=15, minute=55, second=0, microsecond=0)
            
            # If past buy time today, show tomorrow
            if now_et >= buy_time:
                buy_time += timedelta(days=1)
            
            return buy_time.strftime("%H:%M ET")
        else:
            # Accelerated: 10 minutes from last buy
            if self.last_dip_buy_time:
                next_time = self.last_dip_buy_time + timedelta(minutes=10)
                now = datetime.now()
                
                if next_time > now:
                    remaining = (next_time - now).total_seconds() / 60
                    return f"{int(remaining)}분 후"
                else:
                    return "즉시"
            return "즉시"
'''

# Find the position to insert (before the last line or before to_dict method)
if 'def to_dict(self)' in content:
    # Insert before to_dict
    insert_pos = content.rfind('    def to_dict(self)')
    new_content = content[:insert_pos] + methods_to_add + '\n    ' + content[insert_pos:]
else:
    # Insert at the end of the class
    # Find last method and insert after it
    lines = content.split('\n')
    # Find the last line that's not empty
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip():
            insert_line = i + 1
            break
    lines.insert(insert_line, methods_to_add)
    new_content = '\n'.join(lines)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Methods added to bot_controller.py")
