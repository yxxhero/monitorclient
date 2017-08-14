#!/usr/bin/env python2.7
# coding:utf-8
import socket
import commands
import sys
import os
import psutil
import atexit
import platform
import urllib
import urllib2
import time
import argparse
import signal
import logging
from setproctitle import setproctitle,getproctitle
from configobj import ConfigObj
from daemon import Daemon
#from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
setproctitle("monitorclient")
if 'threading' in sys.modules:
    del sys.modules['threading']
class system_info(object):
    def __init__(self,description):
        self.systeminfo = {}
        self.hostname = ''
        self.ip_dict = {}
        self.swap_info={}
        self.cpu_info = {}
        self.system_name = ''
        self.process_info = {}
        self.mem_info = {}
        self.disk_info =[] 
        self.user_info=[]
        self.description=description
	
    def get_sysinfo(self):
        uptime = int(time.time() - psutil.boot_time())
        sysinfo = {
            'uptime': uptime,
            'hostname': socket.gethostname(),
            'os': platform.platform(),
            'mempercent':psutil.virtual_memory().percent,
            'cpu_usage' : psutil.cpu_percent(),
            'root_usage':psutil.disk_usage('/').percent
        }

        return sysinfo
    def get_portinfo(self):
        checkport=commands.getstatusoutput('netstat -tnlp')
        if int(checkport[0]) == 0:
            portinfolist=[]
            for line in checkport[1].split("\n")[2:]:
                portinfolist.append((line.split()[6].split("/")[1],line.split()[3].split(":")[-1]))
            return portinfolist

    def get_disk_info(self):
        disks=psutil.disk_partitions()
        self.disk_info=[]
        for disk in disks:
            self.disk_info.append(
                {'device':disk.device,
                 'mountpoint':disk.mountpoint,
                 'fstype':disk.fstype,
                 'opts':disk.opts,
                 'total':psutil.disk_usage(disk.mountpoint).total/1024/1024,
                 'used':psutil.disk_usage(disk.mountpoint).used/1024/1024,
                 'free':psutil.disk_usage(disk.mountpoint).free/1024/1024,
                 'percent':psutil.disk_usage(disk.mountpoint).percent
            })
        return self.disk_info
    
    def get_system_name(self):
        self.system_name =''.join(platform.linux_distribution()[0:2]) 
        return self.system_name
    def get_user_info(self):
        self.user_info=[]
        for user in psutil.users():
            self.user_info.append({
                'user':user.name,
                'terminal':user.terminal,
                'host':user.host,
                'started':time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(user.started))
            })
        return self.user_info


    def get_mem_info(self):
        self.mem_info['total'] = psutil.virtual_memory().total/1024/1024
        self.mem_info['available'] = psutil.virtual_memory().available/1024/1024
        self.mem_info['used'] = psutil.virtual_memory().used/1024/1024
        self.mem_info['free'] = psutil.virtual_memory().free/1024/1024
        self.mem_info['active'] = psutil.virtual_memory().active/1024/1024
        self.mem_info['inactive'] = psutil.virtual_memory().inactive/1024/1024
        self.mem_info['buffers'] = psutil.virtual_memory().buffers/1024/1024
        self.mem_info['cached'] = psutil.virtual_memory().cached/1024/1024
        self.mem_info['shared'] = psutil.virtual_memory().shared/1024/1024
        return self.mem_info

    def get_process_info(self,*args,**kwargs):
        ps_list=[]
        list=psutil.process_iter()
        for proc in list:
            ps=proc.as_dict(attrs=['pid', 'name'])['name']
            if ps in args[0]: 
               if ps not in ps_list:
                   ps_list.append(ps)
        for firmitem in args[1]:
            cmd="ps auxf | grep %s| grep -v grep|wc -l" %(firmitem)
            status,output=commands.getstatusoutput(cmd)
            if int(status)==0 and int(output) >= 1:
                ps_list.append(firmitem)
            
            
        return ps_list
		
    def get_hostname(self):
        self.hostname=socket.gethostname()
        return self.hostname

    def get_ip_dict(self):
        if platform.system() == 'Linux':
            for line in os.popen("ip add | grep \"scope global\" ").readlines():
                device = line.split()[-1]
                ip = line.split()[1]
                self.ip_dict[device] = ip
        if platform.system() == 'Windows':
            adapter_num = 0
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                adapter_num = adapter_num + 1
                device = "adapter"+str(adapter_num)
                self.ip_dict[device] = ip
        return self.ip_dict
	
    def get_cpu_info(self):
        self.cpu_info['logical_cores'] = psutil.cpu_count()
        self.cpu_info['physical_cores'] = psutil.cpu_count(logical = False)
        self.cpu_info['load_avg']=' '.join([str(i) for i in os.getloadavg()])
        self.cpu_info['user']=psutil.cpu_times().user
        self.cpu_info['system']=psutil.cpu_times().system
        self.cpu_info['idle']=psutil.cpu_times().idle
        self.cpu_info['iowait']=psutil.cpu_times().iowait
        return self.cpu_info
    def get_swap_info(self):
        self.swap_info['total']=psutil.swap_memory().total/1024/1024
        self.swap_info['used']=psutil.swap_memory().used/1024/1024
        self.swap_info['free']=psutil.swap_memory().free/1024/1024
        self.swap_info['sin']=psutil.swap_memory().sin/1024/1024
        self.swap_info['sout']=psutil.swap_memory().sout/1024/1024
        return self.swap_info


    def get_system_info(self,*args,**kwargs):
        keyprocess=[]
        for pl in args:
            keyprocess.extend(pl)
        self.systeminfo['hostname'] = self.get_hostname()
        self.systeminfo['ip_dict'] = self.get_ip_dict()
        self.systeminfo['cpu_info'] = self.get_cpu_info()
        self.systeminfo['mem_info'] = self.get_mem_info()
        self.systeminfo['system_name'] = self.get_system_name()
        self.systeminfo['disk_info'] = self.get_disk_info()
        self.systeminfo['processlist'] = self.get_process_info(*args,**kwargs)
        self.systeminfo['user_info'] = self.get_user_info()
        self.systeminfo['port_info'] = self.get_portinfo()
        self.systeminfo['description'] = self.description
        self.systeminfo['keyprocess']=keyprocess
        
        return self.systeminfo
    def post_system_info(self,url,data):
        format_data=urllib.urlencode(data)
        req=urllib2.Request(url,format_data)
        response=urllib2.urlopen(req,timeout=3)
        return response 


def client_worker(client,url,pslist):
    response=None
    try:
        client_data=client.get_system_info(pslist,firm_list)
        host_data={'host_info':client_data}
        response=client.post_system_info(url,host_data)
        result=response.read()
    except Exception,e:
        logging.warning(str(e))
    else:
        if int(eval(result)["error"])==0:
            logging.info("上报成功")
        else:
            logging.error("上报失败")
    finally:
        if response:
            response.close()
class pantalaimon(Daemon):
    def restart(self,interval,client,url,pslist):
        self.stop()
        self.start(interval,client,url,pslist)
    def run(self,interval,client,url,pslist):
        atexit.register(self.delpid)  # Make sure pid file is removed if we quit
        pid = str(os.getpid())
        open(self.pidfile, 'w+').write("%s\n" % pid)
        scheduler.add_job(func=client_worker,args=(client,url,pslist), trigger='interval', seconds=interval)
        scheduler.start()
def signal_handler(signum,frame):
    print "agent is going down"
    config=ConfigObj(config_file,encoding='UTF8')
    pidfile=config['client']['pidfile']
    try:
        pf = open(pidfile, 'r')
        pid = int(pf.read().strip())
        pf.close()
    except IOError:
        pid = None
    except SystemExit:
        pid = None
    if not pid:
        message = "pidfile %s does not exist. Not running?\n"
        sys.stderr.write(message % pidfile)

        # Just to be sure. A ValueError might occur if the PID file is
        # empty but does actually exist
        if os.path.exists(pidfile):
            os.remove(pidfile)
    else:
        if os.path.exists(pidfile):
            os.remove(pidfile)

    # Try killing the daemon process
    try:
        i = 0
        while 1:
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.1)
            i = i + 1
            if i % 10 == 0:
                os.kill(pid, signal.SIGHUP)
    except OSError as err:
        if err.errno == errno.ESRCH:
            if os.path.exists(pidfile):
                os.remove(pidfile)
        else:
            print(str(err))
            sys.exit(1)
    print("Stopped")
           

if __name__=='__main__':
    parser = argparse.ArgumentParser(prog='cmdbclient')
    parser.add_argument('--config',default='/opt/cmdb/cmdbclient/etc/cmdbclient.conf',type=str,help='指定配置文件')
    parser.add_argument('action',type=str,choices=['start','restart','stop','run','status'],help='启动方式')
    args=parser.parse_args()
    action=args.action
    config_file=args.config
    config=ConfigObj(config_file,encoding='UTF8')
    interval=int(config['client']['interval'])
    description=config['client']['description']
    host=config['server']['server_host']
    port=config['server']['server_port']
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uri=config['server']['uri']
    url='http://'+host+':'+port+uri
    pidfile=config['client']['pidfile']
    pslist=config['client']['process_list'].split('^')
    firm_list=config['client']['firm_list'].split('^')
    client_info=system_info(description)
#    scheduler = BackgroundScheduler()
    scheduler = BlockingScheduler({'apscheduler.timezone': 'Asia/Shanghai'})
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s',
                        datefmt='%a, %d %b %Y %H:%M:%S',
                        filename=BASE_DIR+'/log/myapp.log',
                        filemode='a')
    pineMarten = pantalaimon(pidfile)
    signal.signal(signal.SIGINT,signal_handler)
    if action == "start":
        pineMarten.start(interval,client_info,url,pslist)
    elif action == "stop":
        pineMarten.stop()
    elif action=="restart":
        pineMarten.restart(interval,client_info,url,pslist)
    elif action=="run":
        pineMarten.run(interval,client_info,url,pslist)
