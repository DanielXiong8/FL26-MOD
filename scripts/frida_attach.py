import frida
import sys
import time

def on_message(msg, data):
    if msg['type'] == 'send':
        print(msg['payload'])
    elif msg['type'] == 'error':
        print(f'ERROR: {msg.get("description", msg)}')
    else:
        print(msg)

def main():
    d = frida.get_device_manager().add_remote_device('127.0.0.1:27042')
    print('[+] connected to device')
    
    session = d.attach('com.football.soccer.league.mod')
    print('[+] attached to game process')
    
    with open(r'C:\FL26_Mod\scripts\frida_hook.js', 'r', encoding='utf-8') as f:
        script_code = f.read()
    
    script = session.create_script(script_code)
    script.on('message', on_message)
    script.load()
    print('[+] hooks active, waiting for events (Ctrl+C to stop)')
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print('stopping...')
        session.detach()

if __name__ == '__main__':
    main()
