import subprocess

try:
    cmd = ['powershell', '-NoProfile', '-Command', 'Get-WmiObject Win32_Process -Filter "name like \'python%\'" | Select-Object ProcessId, CommandLine | Format-Table -AutoSize']
    out = subprocess.check_output(cmd, text=True)
    print(out)
except Exception as e:
    print(f"Error: {e}")
