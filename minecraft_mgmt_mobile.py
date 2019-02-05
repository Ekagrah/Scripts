#!/usr/bin/env python3

## Designed to run from an iOS device with pythonista to a linux hosted server

##------Start user editable section------##

SERV_INSTALLDIR = '/opt/ATLauncher/Servers/SevTechAges_308'
JAR = 'forge-1.12.2-14.23.4.2707-universal.jar'
SERVER_HOSTNAME = '10.0.0.221'

LINUX_USER = 'minecraft'
## key needs to be an openssh compatible format, if key file exists use that otherwise use password
LINUX_USER_KEY = ''
LINUX_USER_PASSWORD = 'password'
SERV_PORT = '25565'
## Requires a running rcon port to validate server is fully ready. Otherwise need to adjust MONITOR function
RCON_SERVER_PORT = '25575'
RCON_PASSWORD = 'secret'

##------End user editable section------##

import argparse
import datetime
import logging
import os
import paramiko
import re
import socket
import struct
import sys
import tempfile
import time

CURR_DATE = time.strftime("%b%d_%H-%M")

class TermColor:
        RED = '\033[93;41m'
        MAGENTA = '\033[35m'
        DEFAULT = '\033[00m'

def VARIABLE_CHK():
    """Verify needed variables have proper value"""
    
    varchk = [SERV_INSTALLDIR, SERVER_HOSTNAME, SERV_PORT, RCON_SERVER_PORT, RCON_PASSWORD, LINUX_USER]
    
    varlist = ["SERV_INSTALLDIR", "SERVER_HOSTNAME", "SERV_PORT", "RCON_SERVER_PORT", "RCON_PASSWORD", "LINUX_USER"]
    
    err_on_var = []
    invalid_var = []
    for id, x in enumerate(varchk):
        if not x:
            err_on_var.append(varlist[id])
            break
        elif id in  ("3", "4"):
            ## if these variables are not integers then flag, converting to float for good measure
            if not float(x).is_integer():
                invalid_var.append(varlist[id])
    
    if err_on_var:
        print(TermColor.MAGENTA)
        print('Missing value for:')
        print(*err_on_var, sep='\n')
        print(TermColor.DEFAULT)
        
    if invalid_var:
        print(TermColor.RED)
        print('Invalid value for:')
        print(*invalid_var, sep='\n')    
        print(TermColor.DEFAULT)
        
    if any((err_on_var, invalid_var)):
        sys.exit(1)
        
VARIABLE_CHK()


def get_args():
    """Function to get action, specified on command line, to take for server"""
    
    ## Assign description to help doc
    parser = argparse.ArgumentParser(description='Script manages various functions taken on remote linux Minecraft server. One action accepted at a time.', allow_abbrev=False)
    
    ## Add arguments. When argument present on command line, then it is stored as True, else returns False
    parser.add_argument(
        '--start', help='Start remote server', action='store_true')
    parser.add_argument(
        '--shutdown', help='Stop remote server', action='store_true')
    parser.add_argument(
        '--restart', help='Restart remote server', action='store_true')
    parser.add_argument(
        '--monitor', help='Reports back if server is running and accessible', action='store_true')
    parser.add_argument(
        '--rcon', help='Launches interactive rcon session', action='store_true')
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files', action='store_true')
    parser.add_argument(
        '--listplayers', help='Lists players that are connected to server', action='store_true')
        
        
    ## Array for argument(s) passed to script
    args = parser.parse_args()
    
    start = args.start
    shutdown = args.shutdown
    restart = args.restart
    monitor = args.monitor
    rcon = args.rcon
    save = args.save
    listplayers = args.listplayers
    ## Return all variable values
    return start, shutdown, restart, monitor, rcon, save, listplayers
    

class ssh:
    """Create ssh connection"""
    client = None
    def __init__(self, server, port, user, password=None):
        "Create ssh connection"
        self.client = paramiko.client.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        if os.path.exists(LINUX_USER_KEY):
            self.client.load_system_host_keys()
            keyfile = paramiko.RSAKey.from_private_key_file(LINUX_USER_KEY)
            self.client.connect(server, port, username=user, pkey=keyfile)
        elif password:
            self.client.connect(server, port, username=user, password=password)
        else:
            print("No valid authenication methods provided")
            sys.exit(2)
    
    def sendCommand(self, command, stdoutwrite=False, parse=False, target=None, timeout=10, recv_size=2048):
        """Method to send command over ssh transport channel"""
        
        parse_return = None
        self.transport = self.client.get_transport()
        self.channel = self.transport.open_channel(kind='session')
        self.channel.settimeout(timeout)
        ## verify channel open or exit gracefully
        try:
            self.channel.exec_command(command)
            self.channel.shutdown(1)
            fd, fp = tempfile.mkstemp()
            f = open(fp, 'a+')
            stdout, stderr = [], []
            while not self.channel.exit_status_ready():
                if self.channel.recv_ready():
                    recvd = self.channel.recv(recv_size).decode("utf-8")
                    stdout.append(recvd)
                    if stdoutwrite:
                        sys.stdout.write(' '.join(recvd))
                    if parse:
                        f.write(recvd)
                
                if self.channel.recv_stderr_ready():
                    stderr.append(self.channel.recv_stderr(recv_size).decode("utf-8"))
                    #raise
            
            while True:
                try:
                    remainder_recvd = self.channel.recv(recv_size).decode("utf-8")
                    if not remainder_recvd and not self.channel.recv_ready():
                        break
                    else:
                        stdout.append(remainder_recvd)
                        
                        if stdoutwrite:
                            sys.stdout.write(' '.join(stdout))
                        if parse:
                            f.write(remainder_recvd)
                except socket.timeout:
                    break
                    
            while True:
                try:
                    remainder_stderr = self.channel.recv_stderr(recv_size).decode("utf-8")
                    if not remainder_stderr and not self.channel.recv_stderr_ready():
                        break
                    else:
                        stderr.append(remainder_stderr)
                except socket.timeout:
                    break
            
            exit_status = self.channel.recv_exit_status()
            
            if parse:
                with open(fp) as f:
                    f.seek(0)
                    pattern = re.compile(target)
                    for line in f:
                        if pattern.match(line):
                            parse_return = True
                            break
                        else:
                            parse_return = False
        except SSHException:
            print(TermColor.RED)
            sys.exit("Connection not opened.")
            
        if parse:
            return parse_return
        else:
            return stdout, stderr, exit_status
    ## end def sendCommand
## end ssh class


def RCON_CLIENT(*args):
    """Remote Console Port access. Limited commands are available. Original code by Dunto, updated/modified by Ekagrah. Minor adjustments for Minecraft output."""
        
    ## DO NOT EDIT THESE VARIABLES UNLESS YOU UNDERSTAND THE CONSEQUENCES
    MESSAGE_TYPE_AUTH = 3
    MESSAGE_TYPE_AUTH_RESP = 2
    MESSAGE_TYPE_COMMAND = 2
    MESSAGE_TYPE_RESP = 0
    MESSAGE_ID = 0
    ## server response timeout in seconds
    RCON_SERVER_TIMEOUT = 3
    
    def sendMessage(sock, command_string, message_type):
        """Packages up a command string into a message and sends it"""
        try:
            command_len = len(command_string)
            byte_command = command_string.encode(encoding='ascii')
            message_size = (4 + 4 + command_len + 2)
            message_format = ''.join(['=lll', str(command_len), 's2s'])
            packed_message = struct.pack(message_format, message_size, MESSAGE_ID, message_type, byte_command, b'\x00\x00')
            sock.sendall(packed_message)
        except socket.timeout:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
    
    
    def getResponse(sock):
        """Gets the message response to a sent command and unpackages it"""
        response_string = None
        response_dummy = None
        response_id = -1
        response_type = -1
        try:
            recv_packet = sock.recv(4)
            tmp_response_size = struct.unpack('=l', recv_packet)
            response_size_val = int(tmp_response_size[0])
            response_size = response_size_val - 9
            message_format = ''.join(['=ll', str(response_size), 's1s'])
            remain_packet = struct.unpack(message_format, sock.recv(response_size_val))
            (response_id,response_type,response_string,response_dummy) = remain_packet
            if (response_string is None or response_string is str(b'\x00')) and response_id is not 2:
                response_string = "(Empty Response)"
        except socket.timeout:
            response_string = "(Connection Timeout)"
        
        return (response_string, response_id, response_type)

    
    ## Begin main loop
    interactive_mode = True
    sock = ''
    while interactive_mode:
        command_string = None
        response_string = None
        response_id = -1
        response_type = -1
        if args:
            interactive_mode = False
            command_string = str(args[0])
            print("RCON command sent: {}".format(command_string))
        else:
            command_string = input("RCON Command: ")
            if command_string in ('exit', 'Exit'):
                
                if sock:
                    sock.shutdown(socket.SHUT_RDWR)
                    sock.close()
                print("Exiting rcon client...\n")
                break
            elif command_string in ('') or not command_string:
                continue

        try:
            sock = socket.create_connection((SERVER_HOSTNAME, RCON_SERVER_PORT))
        except ConnectionRefusedError:
            #print("Unable to make RCON connection")
            raise
            break
        
        sock.settimeout(RCON_SERVER_TIMEOUT)

        sendMessage(sock, RCON_PASSWORD, MESSAGE_TYPE_AUTH)
        response_string,response_id,response_type = getResponse(sock)
        response_string,response_id,response_type = getResponse(sock)

        sendMessage(sock, command_string, MESSAGE_TYPE_COMMAND)
        response_string,response_id,response_type = getResponse(sock)
        response_txt = response_string.decode(encoding=('UTF-8'))[:-1]
        
        if interactive_mode:
            print(response_txt)
        else:
            sock.shutdown(socket.SHUT_RDWR)
            sock.close()
            return response_txt
    ## end main loop
## end def RCON_CLIENT


def LIST_PLAYERS():
    """List players connected to server"""
    
    try:
        PLAYER_LIST = RCON_CLIENT('/list')
        print(PLAYER_LIST)
    except:
        err = sys.exc_info()[1]
        print("Error: {}".format(err))


def CHECK_PLAYERS():
    """Check if players are connected to server"""
    
    chktimeout = 9
    while chktimeout > 0:
        try:
            PLAYER_LIST = RCON_CLIENT('/list')
        except:
            err = sys.exc_info()[1]
            print("Error: {}".format(err))
            break
        pattern = re.compile(".*0/[0-9]+.*")
        if pattern.search(PLAYER_LIST):
            break
        else:
            print(PLAYER_LIST)
            time.sleep(20)
            chktimeout -= 1
    if chktimeout == 0:
        print('Timeout waiting for users to log off')
        return False
    elif err:
        return False
    else:
        return True
        

def SERV_MONITOR():
    """Checks on status of server"""
    ## increase as needed, especially when using mods
    upcounter = 12
    SERV_STATUS_CHK = sshconnect.sendCommand("/usr/bin/pgrep -x tmux 2>/dev/null", parse=True, target="[0-9]*")
    if SERV_STATUS_CHK:
        print("Server is running")
        while True:
            PORT_CHK = sshconnect.sendCommand("/bin/netstat -l 2>/dev/null | /bin/grep -E '.*:{}.*'".format(RCON_SERVER_PORT), parse=True, target=".*:{}.*".format(RCON_SERVER_PORT))
            if PORT_CHK:
                print("Server is up and should be accessible")
                break
            else:
                if upcounter > 0:
                    print("Waiting on server...")
                    time.sleep(20)
                    upcounter -= 1
                else:
                    print("Server not up yet, manually monitor status...")
                    break
    else:
        print("Server does not seem to be running")


def UPSERVER():
    TMUX_CHK = sshconnect.sendCommand("/usr/bin/tmux list-session | /usr/bin/cut -d \: -f 1", parse=True, target="minecraft")
    if TMUX_CHK:
        print("Server seems to be running already")
    else:
        print("Starting server")
        sshconnect.sendCommand('cd {0} ; tmux new-session -d -x 23 -y 80 -s minecraft java -server -Xmx6G -Xms6G -XX:+UseG1GC -XX:ParallelGCThreads=2 -XX:MaxGCPauseMillis=80 -jar {1} nogui'.format(SERV_INSTALLDIR, JAR))
        ## -XX:MaxPermSize=1G, -XX:MaxMetaspaceSize=512M, -XX:+UseConcMarkSweepGC, -Xms512M
        
        SERV_MONITOR()
    

def DOWNSERVER():
    """Shutdown server instance"""
    
    downcounter = 7
    UPCHK = sshconnect.sendCommand("/usr/bin/tmux list-session | /usr/bin/cut -d \: -f 1", parse=True, target="minecraft")
    if UPCHK:
        print("Shutting down server...")
        try:
            RCON_CLIENT("/stop")
            time.sleep(10)
        except:
            err = sys.exc_info()[1]
            print("Error: {}".format(err))
    else:
        print("Unable to find running server")
    while True:
        if err:
            break
        
        ALT_CHK = sshconnect.sendCommand("/usr/bin/pgrep -x java 2>/dev/null", parse=True, target="[0-9]*")
        if ALT_CHK:
            if downcounter == 0:
                print('Forcfully killing server instance')
                sshconnect.sendCommand("for i in $(/usr/bin/pgrep -c java 2>/dev/null); do kill -9 $i; done")
                SERV_MONITOR()
                break
            else:
                print("Waiting for server to go down gracefully")
                time.sleep(10)
                downcounter -= 1
        else:
            print("Definitely no running server")
            break


def RESTART_SERVER():
    """Check if players have disconnected then shutdown and start server"""
    
    try: 
        RCON_CLIENT("/say Server going down for maintenance in 3 minutes")
        
        if CHECK_PLAYERS():
            print("Proceeding to restart server.\n")
            DOWNSERVER()
            SERV_MONITOR()
            time.sleep(10)
            UPSERVER()
    except:
        err = sys.exc_info()[1]
        print("Error: {}".format(err))


def FNC_DO_SAVE():
    """Archive world, player, and configuration files into a tar"""
    
    ## backups handled by aromabackups mod
    ## SERV_SAVE_DIR = "{}/backups/{}/".format(SERV_INSTALLDIR, WORLD_NAME)


#============================#

orig_sys_argv = sys.argv
cmdline = ''
sshconnect = ''
while True:
    sys.argv = orig_sys_argv
    working_sys_argv = orig_sys_argv
    mylist = []
    command_string = ''
    if len(sys.argv) < 2:
        command_string = input("Command: ")
        if command_string in ('exit', 'Exit'):
            if sshconnect:
                sshconnect.client.close()
            sys.exit('Exiting mgmt program')
        elif not command_string:
            continue
        else:
            mylist.append('--{}'.format(command_string))
            sys.argv = [working_sys_argv[0]] + mylist
    elif len(sys.argv) == 2:
        cmdline = True
    else:
        print('Too many arguments provided.')
        print(' --help, for usage')
        break
    
    ## Run get_args
    start, shutdown, restart, monitor, rcon, save, listplayers = get_args()
            
    if listplayers:
        LIST_PLAYERS()
        if cmdline:
            sys.exit(0)
        else:
            continue
    elif rcon:
        RCON_CLIENT()
        if cmdline:
            sys.exit(0)
        else:
            continue
    
    ## Create ssh connection
    sshconnect = ssh(SERVER_HOSTNAME, 22, LINUX_USER, LINUX_USER_PASSWORD)
    
    if start:
        UPSERVER()
    elif shutdown:
        DOWNSERVER()
    elif restart:
        RESTART_SERVER()
    elif monitor:
        SERV_MONITOR()
    elif save:
        #FNC_DO_SAVE()
        print("Not needed for modded server, backups taken periodically")

    if cmdline:
        ## Close ssh connection
        sshconnect.client.close()
        sys.exit(0)
