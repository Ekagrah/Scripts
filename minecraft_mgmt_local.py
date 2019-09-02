#!/usr/bin/env python3
## see my linux ark server documentation on how linux server is set up

##------Start user editable section------##

WORLD_NAME = 'RADical'
SERV_INSTALLDIR = '/opt/curse-forge/RAD-1.30/'
JAR = 'forge-1.12.2-14.23.5.2838-universal.jar'
SERVER_HOSTNAME = '192.168.0.0'

SERV_PORT = '25565'
## Requires a running rcon port to validate server is fully ready. Otherwise need to adjust MONITOR function
RCON_SERVER_PORT = '25575'
RCON_PASSWORD = 'secret'

## Email address to send and receive from
EMAIL_ADDR = 'email@example.com'

## Directory where save data stored
SERV_SAVE_DIR = '/home/user/Documents/mcsavedata'

## Manage saves, logrotate type fashion
MANAGE_SAVES = True
save_days_to_keep = 2
save_hours_to_keep = 3

##------End user editable section------##

import argparse
import datetime
import os
from pathlib import Path
import re
import socket
import struct
import subprocess
import sys
import tempfile
import time

CURR_DATE = time.strftime("%b%d_%H-%M")
## In Python 3.5+ you can use pathlib.Path.home()
home = str(Path.home())
devnull = open(os.devnull, 'w')


class TermColor:
        RED = '\033[93;41m'
        MAGENTA = '\033[35m'
        DEFAULT = '\033[00m'

def VARIABLE_CHK():
    """Verify needed variables have proper value"""
    
    varchk = [SERV_INSTALLDIR, JAR, WORLD_NAME, SERV_PORT, RCON_SERVER_PORT, RCON_PASSWORD, MANAGE_SAVES, SERV_SAVE_DIR]
    
    varlist = ["SERV_INSTALLDIR", "JAR", "WORLD_NAME", "SERV_PORT", "RCON_SERVER_PORT", "RCON_PASSWORD", "MANAGE_SAVES", "SERV_SAVE_DIR"]
    
    err_on_var = []
    invalid_var = []
    for id, x in enumerate(varchk):
        if not x:
            err_on_var.append(varlist[id])
            break
        elif id in ("3", "4"):
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
        '--email', help='Email information about server', action='store_true')
    parser.add_argument(
        '--save', help='Makes a copy of server config, map save data, and player data files in .tgz format to the specified path', action='store_true')
    parser.add_argument(
        '--listplayers', help='Lists players that are connected to server', action='store_true')
    parser.add_argument(
        '--auto', help='Function to use as cronjob to auto-start server if not running', action='store_true')
        
        
    ## Array for argument(s) passed to script
    args = parser.parse_args()
    
    start = args.start
    shutdown = args.shutdown
    restart = args.restart
    monitor = args.monitor
    rcon = args.rcon
    email = args.email
    save = args.save
    listplayers = args.listplayers
    auto = args.auto
    ## Return all variable values
    return start, shutdown, restart, monitor, rcon, email, save, listplayers, auto
    
    if not len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)


def SERV_STATUS_CHK():
    """Method for verifying server is running"""
    
    output = ''
    try:
        output = subprocess.check_output("/usr/bin/tmux list-session 2>/dev/null | /usr/bin/cut -d \: -f 1", shell=True).decode("utf-8")
    except subprocess.CalledProcessError:
        return False
        
    if not output:
        return False
    else:   
        pattern = re.compile("minecraft")
        for line in output.split('\n'):
                if pattern.match(line):
                    return True
                    break
                else:
                    return False
                

def RCON_CLIENT(*args):
    """Remote Console Port access. Limited commands are available. Original code by Dunto, updated/modified by Ekagrah. Minor adjustments for Minecraft output."""
    
    if not SERV_STATUS_CHK():
        sys.exit("Server not running, no RCON available")
        
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
        except:
            response_string = "(Error) Response ID: {}".format(response_id)
        
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
            elif command_string in ('help','h','Help'):
                print('\tUse exit or Exit to quit.')
                print('Tested commands: /deop, /help, /kick, /msg, /op, /time, /save-all, /say, /stop, /weather')
                continue
            elif command_string in ('') or not command_string:
                continue

        try:
            sock = socket.create_connection(("127.0.0.1", RCON_SERVER_PORT))
        except ConnectionRefusedError:
            raise
            break
        
        sock.settimeout(RCON_SERVER_TIMEOUT)

        sendMessage(sock, RCON_PASSWORD, MESSAGE_TYPE_AUTH)
        response_string,response_id,response_type = getResponse(sock)
        response_string,response_id,response_type = getResponse(sock)

        sendMessage(sock, command_string, MESSAGE_TYPE_COMMAND)
        response_string,response_id,response_type = getResponse(sock)
        try:
            response_txt = response_string.decode(encoding=('UTF-8'))[:-1]
        except AttributeError:
            response_txt = response_string
        
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
    
    err = ''
    try:
        PLAYER_LIST = RCON_CLIENT('/list')
        print(PLAYER_LIST)
    except:
        err = sys.exc_info()[1]
        print("Error: {}".format(err))


def CHECK_PLAYERS():
    """Check if players are connected to server. Returns True when no one is connected"""
    
    err = ''
    chktimeout = 9
    while chktimeout > 0:
        try:
            PLAYER_LIST = RCON_CLIENT('/list')
        except:
            err = sys.exc_info()[1]
            print("Error: {}".format(err))
            break
        pattern = re.compile(".*0.*[0-9]+.*")
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


def UPSERVER():
    """Make temporary file so command can be called from there and will run independently from python script"""
    
    ## Continuing to use tmux since access to the server's local console is needed
    launchcmd = '''#!/bin/bash
    cd {}
    tmux new-session -d -x 23 -y 80 -s minecraft java -server -Xmx10G -Xms6G -XX:+UseG1GC -XX:ParallelGCThreads=2 -XX:MaxGCPauseMillis=80 -jar {} nogui
    exit 0'''.format(SERV_INSTALLDIR, JAR)
    ## can add option listed below to accept fml changes automatically
    ## -Dfml.queryResult=confirm
    ## or use use the server console accessed by:
    ## tmux attach-session -t minecraft
    ## ctrl + b then d to disconnect
    
    tmpscript = tempfile.NamedTemporaryFile('wt')
    tmpscript.write(launchcmd)
    ## 
    tmpscript.flush()
    
    print('\nStarting server')
    subprocess.Popen(['/bin/bash', tmpscript.name],
        close_fds=True,
        preexec_fn=os.setsid,
        )


def SERV_MONITOR():
    """Checks on status of server"""
    
    ## Increase as needed, especially for community packs/mods
    upcounter = 14
    if SERV_STATUS_CHK():
        print("Server is running")
    else:
        sys.exit("Server does not seem to be running")
    
    while True:
        rpattern = '.*:{}.*java.*'.format(RCON_SERVER_PORT)
        
        PORT_CHK = subprocess.run("/bin/netstat -pl 2>/dev/null | /bin/grep -E '{}'".format(rpattern), stdout=subprocess.PIPE, shell=True) 
        
        pattern = re.compile(rpattern)
        if pattern.search(PORT_CHK.stdout.decode("utf-8")):
            print("Server is up and should be accessible")
            sys.exit()
        else:
            if upcounter > 0:
                print("Waiting on server...")
                time.sleep(20)
                upcounter -= 1
            else:
                sys.exit("Server not up yet, manually monitor status...")


def DOWNSERVER():
    """Attempt to gracefully shutdown server"""
    
    err = ''
    downcounter = 7
    try:
        print("Shutting down server...")
        RCON_CLIENT("/stop")
        time.sleep(5)
    except:
        err = sys.exc_info()[1]
        sys.exit("Error: {}".format(err))
            
    while True:
        if SERV_STATUS_CHK():
            print("Waiting for server to go down gracefully")
            time.sleep(10)
            downcounter -= 1
        else:
            print("Definitely no server to shutdown")
            return False
        if downcounter == 0:
            if SERV_STATUS_CHK():
                print("Running server still found, forcefully killing server process.")
                subprocess.run("for i in $(/usr/bin/pgrep -x java); do kill -9 $i; done", shell=True, stdout=subprocess.PIPE)
                return False
            if SERV_STATUS_CHK():
                print("Unable to take server down, manual shutdown needed")
                print("Example: run '/stop' via rcon or console")
                sys.exit(3)


def RESTART_SERVER():
    """Check if players have disconnected then shutdown then start server"""
    
    if SERV_STATUS_CHK():
        RCON_CLIENT("/say Server going down for maintenance in 3 minutes")
        if CHECK_PLAYERS():
            print("Proceeding to restart server.\n")
            DOWNSERVER()
            UPSERVER()
            SERV_MONITOR()
    else:
        print("Unable to find running server to restart")


def EMAIL(content, subject):
    import smtplib
    import email.utils
    from email.mime.text import MIMEText
    
    if not SERV_STATUS_CHK():
        sys.exit("Server not running, not sending email")
    
    msg = MIMEText(content)
    msg['To'] = email.utils.formataddr(('Server Manager', EMAIL_ADDR))
    msg['From'] = email.utils.formataddr(('Minecraft Server', EMAIL_ADDR))
    msg['Subject'] = subject
    
    ## To send via SSL use SMTP_SSL()
    server = smtplib.SMTP()
    ## Specifying an empty server.connect() statment defaults to ('localhost', '25')
    server.connect()
    ## Send debug to terminal
    #server.set_debuglevel(True)
    
    try:
        server.sendmail(EMAIL_ADDR, [EMAIL_ADDR], msg.as_string())
    finally:
        server.quit()


def EMAIL_STATS():
    def SUBPROC_CMD(command):
        output = subprocess.check_output(command, shell=True)
        return output.decode("utf-8")
    
    EMAIL_DATE = time.strftime("%F-%R")
    fd, fp = tempfile.mkstemp()
    f = open(fp, 'a+')
    
    f.write(RCON_CLIENT("/list"))
    f.write("\n------\n")
    f.write("CPU Info:\n")
    f.write(SUBPROC_CMD("/bin/cat /proc/cpuinfo | /usr/bin/head -15 | /usr/bin/awk '/model name/{{print}} ; /cpu cores/{{print}}'"))
    f.write("\n------\n")
    ## top > f > disable columns with space > esc > e and E to adjust memory display > W to save
    f.write(SUBPROC_CMD("/usr/bin/top -b -n 1 | awk 'BEGIN {{}}; FNR <= 7; /java/{print}'"))
    f.write("\n------\n")
    f.write(SUBPROC_CMD("/usr/bin/iostat -N -m"))
    f.write("\n------\n")
    f.write(SUBPROC_CMD("/bin/df -h --exclude-type=tmpfs --total"))
    f.write("\n------\n")
    f.write(SUBPROC_CMD("/usr/bin/du -h --max-depth=1 /opt 2>/dev/null"))
    f.seek(0)
    
    EMAIL(f.read(), "Minecraft Server report as of {}".format(EMAIL_DATE))
    
    os.remove(fp)
    
    
def SAVE_MGMT():
    '''Ensure that there is one save per day for each of the last 5 days. Plus a save for each of the last 6 hours.
    Similar functionality to linux logrotate'''

    def MTIME_COMP(COMP_LIST = [], *args):
        TMP_LIST = []
        for c in COMP_LIST:
            TMP_LIST.append(''.join([SERV_SAVE_DIR, "/", c]))
        ## find newest
        NEWEST_TD = max(TMP_LIST, key=os.path.getmtime)
        ## remove newest from list
        TMP_LIST.remove(NEWEST_TD)
        for id, n in enumerate(TMP_LIST):
            TMP_LIST[id] = re.sub('{}/'.format(SERV_SAVE_DIR), "", n)
        ## set all remaining others to be removed
        for d in TMP_LIST:
            SAVE_ROTATE.append(d)
    
    now = int(time.time())
    today = time.strftime("%Y,%-m,%d")
    ## find yesterday at 11pm
    yesterday = datetime.datetime.strptime('{},0,0'.format(today), '%Y,%m,%d,%H,%M') - datetime.timedelta(seconds=3600)
    ## get epoch time for yesterday variable
    eleventh_hour = int(yesterday.timestamp())
    
    SAVE_ROTATE = []
    DAY_CLEAN = []
    WEEK_CLEAN =[]
    time_hours_to_keep = int(3600 * int(save_hours_to_keep))
    time_days_to_keep = int(86400 * int(save_days_to_keep))
    
    for f in os.listdir(SERV_SAVE_DIR):
        SAVE_MTIME = os.path.getmtime(r'{}/{}'.format(SERV_SAVE_DIR, f))
        ## 11pm the day before ± 5 min
        if (eleventh_hour - 300) < SAVE_MTIME < (eleventh_hour + 300):
            continue
        ## if save file between 1 day and X hours old = keep save for current hour + X hours back
        elif (now - 86400) < SAVE_MTIME < (now - time_hours_to_keep):
            DAY_CLEAN.append(f)
        ## if save file older than X days
        elif SAVE_MTIME < (now - time_days_to_keep):
            WEEK_CLEAN.append(f)
        ## should leave a gap of X days where files are not considered
        else:
            continue

    if DAY_CLEAN: 
        print("Attempting to clean up recent files")
        MTIME_COMP(DAY_CLEAN)
    if WEEK_CLEAN: 
        print("Attempting to clean up the last week's files")
        MTIME_COMP(WEEK_CLEAN)
    
    if SAVE_ROTATE:
        print('Found {} file(s) to remove'.format(len(SAVE_ROTATE)))
        
        #EMAIL(SAVE_ROTATE, "Minecraft Server delete report {}".format(EMAIL_DATE))
        
        for i in SAVE_ROTATE:
            i = ''.join([SERV_SAVE_DIR, "/", i])
            if os.path.isfile(i) and i.endswith(".tgz"):
                try:
                    os.remove(i)
                    print("Removed {}".format(i))
                except:
                    print("Unable to remove {}".format(i))


def SAVE_ACTIONS():
    """Archive world, player, and configuration files into a gz compressed tar
    
    Intended to run as a cronjob every hour with MANAGED_SAVES = True
    m h  dom mon dow   command
    0 */2 * * * /path/to/self --save
    
    Mod default path = "{}/backups/{}".format(SERV_INSTALLDIR, WORLD_NAME)
    See: config/ftbbackups.cfg or config/aroma1997/aromabackup.cfg
    """
    
    import fnmatch
    from shutil import copytree, rmtree
    import tarfile
    
    def make_tarfile(output_filename, source_dir):
        with tarfile.open(output_filename, "w:gz") as tar:
            tar.add(source_dir, arcname=os.path.basename(source_dir))
            
    def RECENT_SAVE(file, savetime):
        ITEM_MTIME = os.path.getmtime(file)
        CHECK_SAVE = (time.time() - ITEM_MTIME)
        if CHECK_SAVE <= savetime:
            return True
        else:
            return False
    
    def IGNORE_STUFF():
        def _IGNORE_STUFF(src, files):
            ignore_list = ['mods', 'libraries']
            ignore_list.extend(fnmatch.filter(files, '*.jar'))
            return ignore_list
        return _IGNORE_STUFF
        
    if not SERV_SAVE_DIR:
        sys.exit('No save directory provided')
    
    if SERV_STATUS_CHK():
        ## for versions >1.7
        RCON_CLIENT("/save-all flush")
        #RCON_CLIENT("/save-all")
        time.sleep(2)
    else:
        ## best indicator of recent activity is playerdata
        if not RECENT_SAVE(r'{}/{}/level.dat_old'.format(SERV_INSTALLDIR, WORLD_NAME), 90):
            sys.exit('No changes to server, skipping save.')
    
    tardir = "{}/{}-{}/".format(SERV_SAVE_DIR, WORLD_NAME, CURR_DATE)
    TAR_FILE = '{}/backup-{}-{}.tgz'.format(SERV_SAVE_DIR, WORLD_NAME, CURR_DATE)
    
    print('Copying files...')
    
    try:
        copytree(SERV_INSTALLDIR, tardir, ignore=IGNORE_STUFF())
    except Exception as e:
        capture_traceback = traceback.format_exception()
        raise
    
    try:
        print("Making tarball...")
        make_tarfile(TAR_FILE, '{}'.format(tardir))
    except FileExistsError:
        sys.exit("Unable to make tarball...")
    
    if os.path.exists(TAR_FILE):
        print("Successfully made save bundle - {}".format(TAR_FILE))
        rmtree("{}".format(tardir), ignore_errors=True)
    else:
        sys.exit("Tarball create failed...")
    
    if MANAGE_SAVES:
        SAVE_MGMT()
        
        
def AUTO_START():
    '''If server not runninng, start it. Intended to run as a cronjob'''
    
    if not SERV_STATUS_CHK():
        email_body = None
        try:
            UPSERVER()
        except Exception as e:
            capture_traceback = traceback.format_exception(*sys.exc_info())
            email_body = '\n'.join('Unable to auto-start server', capture_traceback)
        else:
            email_body = 'Auto start required, monitor server and check logs'
        finally:
            EMAIL(email_body, 'Minecraft Server auto-start')
    else:
        sys.exit('No need to auto-start')


#============================#
## Run get_args
start, shutdown, restart, monitor, rcon, email, save, listplayers, auto = get_args()

if listplayers:
    LIST_PLAYERS()
    sys.exit()
elif rcon:
    RCON_CLIENT()
    sys.exit()


if start:
    if SERV_STATUS_CHK():
        sys.exit("Server seems to be running already")
    else:
        UPSERVER()
        time.sleep(3)
        SERV_MONITOR()
elif shutdown:
    if SERV_STATUS_CHK():
        RCON_CLIENT("/say Server shutting down in 3 minutes")
        if CHECK_PLAYERS():
            DOWNSERVER()
elif restart:
    RESTART_SERVER()
elif monitor:
    SERV_MONITOR()
elif email:
    EMAIL_STATS()
elif save:
    SAVE_ACTIONS()
    #print("Not needed for modded server, backups taken periodically")
elif auto:
    AUTO_START()
else:
    print('No actions provided, none taken.')
    print('See help, --help, for usage')

