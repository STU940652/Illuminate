import win32serviceutil
import servicemanager
import win32event
import win32service
import win32evtlogutil
import traceback
import datetime
import subprocess
import os

# If this doesn't work:
# copy c:\Python37\Lib\site-packages\pywin32_system32\pywintypes37.dll c:\Python37\Lib\site-packages\win32

class IlluminateService(win32serviceutil.ServiceFramework):
    _svc_name_ = "IlluminateService"
    _svc_display_name_ = "Illuminate Server"
    _svc_description_ = "Web control for MODBUS/PowerLink devices."

    @classmethod
    def parse_command_line(cls):
        '''
        ClassMethod to parse the command line
        '''
        win32serviceutil.HandleCommandLine(cls)

    def __init__(self, args):
        '''
        Constructor of the winservice
        '''
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.log("Init done")

    def SvcStop(self):
        '''
        Called when the service is asked to stop
        '''
        try:
            self.log("Stopping service...")
            self.subprocess.terminate()
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)
        except:
            self.log(traceback.format_exc())
            
    def SvcDoRun(self):
        '''
        Called when the service is asked to start
        '''
        try:
            self.log(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Illuminate.log'))
            self.log("Starting service...")
            r = servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                                  servicemanager.PYS_SERVICE_STARTED,
                                  (self._svc_name_, ''))
            self.subprocess = subprocess.Popen(r'py -3 Illuminate.py', 
                cwd = os.path.dirname(os.path.realpath(__file__)),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True)
            while not self.subprocess.poll():
                self.log(self.subprocess.stdout.readline())
        except:
            self.log(traceback.format_exc())

    def log(self, s):
        with open (os.path.join(os.path.dirname(os.path.realpath(__file__)), 'Illuminate.log'), 'at') as f:
            f.write("%s: %s\n" % (str(datetime.datetime.now()), s))

# entry point of the module: copy and paste into the new module
# ensuring you are calling the "parse_command_line" of the new created class
if __name__ == '__main__':
    IlluminateService.parse_command_line()
