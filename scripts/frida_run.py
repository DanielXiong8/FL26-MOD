import frida, sys, time

def on_message(msg, data):
    if msg['type'] == 'send':
        print(msg['payload'])
    elif msg['type'] == 'error':
        desc = msg.get('description', str(msg))
        print('ERROR: ' + desc)

def main():
    d = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
    print('[+] connected')
    
    # Find game PID
    import subprocess
    result = subprocess.run(['adb', 'shell', 'pidof', 'com.football.soccer.league.mod'], 
                          capture_output=True, text=True)
    pid = int(result.stdout.strip())
    print(f'[+] game pid={pid}')
    
    session = d.attach(pid)
    print('[+] attached')
    
    with open(r'C:\FL26_Mod\scripts\frida_hook.js', 'r', encoding='utf-8') as f:
        code = f.read()
    
    script = session.create_script(code)
    script.on('message', on_message)
    script.load()
    print('[+] hooks installed, waiting 30s...')
    time.sleep(30)
    print('[*] done')
    session.detach()

if __name__ == '__main__':
    main()
