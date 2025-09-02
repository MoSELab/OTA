import paho.mqtt.client as mqtt
import os, base64
import time
from ab_can import Kvaser
from ab_can import split_data_into_chunks
from tqdm import tqdm
from elftools.elf.elffile import ELFFile
import tempfile

name_topic = "updates/name"
file_topic = "updates/file"
hash_topic = "updates/hash"
userId = "admin"
userPw = "1234"
brokerIp = '192.168.34.223'
port = 1883
tmp_path ="tmp"

file_name = None
file_hash = None
file_data = None
flag = 1

def on_connect(client, userdata, flags, reasonCode):
    if reasonCode == 0:
        print("Connected successfully.")
        client.subscribe("updates/#")

    else:
        print(f"Failed to connect, return code {reasonCode}")

def on_disconnect(client,userdata,flags,rc = 0):
    print(str(rc)+'/')

def send_file(bin_path):
    with open(bin_path,'rb') as bin_file:
        message = bin_file.read()
    transmitter = Kvaser()
    chunks = split_data_into_chunks(message)
    print(1)
    command = bytearray(b'\xff\x00\xff\x00\xff\x00\xff\x00')
    transmitter.transmit_data(123,command)
    time.sleep(1)
    print(2)
    data_size = len(message).to_bytes(4, byteorder='big')
    transmitter.transmit_data(113,data_size)
    time.sleep(0.01)
    print(3)
    for chunk in tqdm(chunks):
        transmitter.transmit_data(112,bytearray(chunk))
        time.sleep(0.015)
    time.sleep(1)

def extract_bin_from_elf(elf_data):
    # 바이너리 데이터를 임시 파일로 저장
    with tempfile.NamedTemporaryFile(delete=False) as temp_elf:
        temp_elf.write(elf_data)
        temp_elf_path = temp_elf.name

    # .bin 파일로 변환
    bin_file_path = temp_elf_path + ".bin"
    with open(temp_elf_path, 'rb') as f:
        elf = ELFFile(f)
        with open(bin_file_path, 'wb') as bf:
            for segment in elf.iter_segments():
                if segment['p_type'] == 'PT_LOAD':  # Loadable segment
                    bf.write(segment.data())

    # 임시 .elf 파일 삭제
    os.remove(temp_elf_path)
    return bin_file_path
    

def on_message(client, userdata, msg):
    global file_name, file_hash, file_data, flag

    try:
        payload = msg.payload.decode('utf-8')
        topic = msg.topic

        if topic == name_topic:
            file_name = payload
            print(file_name)
            
        elif topic == hash_topic:
            file_hash = payload
            print(file_hash)
            
        elif topic == file_topic:
            file_data = base64.b64decode((payload))
            print(file_data)
    except:
        pass

    if file_name and file_data:
        print(file_name)
        tmp_dir = os.path.join(os.getcwd(), "temporary")
        os.makedirs(tmp_dir, exist_ok= True)
        file_path = os.path.join(tmp_dir, file_name)
        with open(file_path, 'wb') as file:
            file.write(file_data)

        while(flag):
            try:
                send_file(file_path)
                flag = 0
            except:
                print("Retry send file")
                time.sleep(5)

        file_name, file_hash, file_data = None, None, None
        flag = 1
        clear_screen()
        print("Ready for new update")  

def clear_screen():
    if os.name == 'nt':  # Windows인 경우
        os.system('cls')
    else:  # UNIX 계열 (Linux, macOS 등)
        os.system('clear')

def main():                      
    client = mqtt.Client()
    client.username_pw_set(userId, userPw)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(brokerIp,port, keepalive=60)
    client.loop_forever()

if __name__ == "__main__":
    clear_screen()
    tmp_dir = os.path.join(os.getcwd(), tmp_path)
    os.makedirs(tmp_dir, exist_ok = True)
    main()