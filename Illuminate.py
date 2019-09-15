#! /usr/bin/python3
import flask
import flask_login
import flask_socketio
import traceback
import json
import os.path
import glob
from pymodbus.client.sync import ModbusTcpClient

# simple user model
class User(flask_login.UserMixin):
    def __init__(self, id):
        self.id = id
        self.name = settings['username']
        self.password = settings['password']
        
    def __repr__(self):
        return "%d/%s" % (self.id, self.name)

# Init Global variables
DEBUG = False
settings_file = './settings.json'
main_thread = None
modbus_client = None

temp_on_off = 'OFF'

settings = {
    'ip_address': '192.168.1.1',
    'tcp_port': 504,
    'zone_title1': 'Zone 1',
    'username': 'admin',
    'password': 'password'
    }


# Init Flask and family
app = flask.Flask(__name__)
# config
app.config.update(
    DEBUG = False,
    SECRET_KEY = 'rimnqiuqnewiornhf7nfwenjmqvliwynhtmlfnlsklrmqwe'
)
socketio = flask_socketio.SocketIO(app)

# flask-login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "route_login"

# create the user       
user = User(0)


def load_settings():
    global settings
    try:
        with open(settings_file, "rt") as f:
            settings.update(json.load(f))
    except: pass

def send_event_info():
    global temp_on_off
    if not DEBUG:
        try:
            result = modbus_client.read_coils(0,1)
            temp_on_off = "ON" if result.bits[0] else "OFF" 
        except:
            traceback.print_exc()
            temp_on_off = "ERROR"
    socketio.emit('update', {"zone1_status": temp_on_off}, namespace='/ws/zone1')

def main_thread_worker():
    while True:
        send_event_info()
        socketio.sleep(2.0)    
                        
@socketio.on('connect', namespace='/ws/zone1')
def ws_connect():
    global main_thread
    if(main_thread is None):
        main_thread = socketio.start_background_task(target=main_thread_worker)
        
    send_event_info()

@socketio.on('turn_on', namespace='/ws/zone1')
def ws_turn_on(d):
    global temp_on_off
    if DEBUG:
        temp_on_off = "ON"
    else:
        try:
            modbus_client.write_coil(0, True)
        except:
            traceback.print_exc()

    send_event_info()

@socketio.on('turn_off', namespace='/ws/zone1')
def ws_turn_off(d):
    global temp_on_off
    if DEBUG:
        temp_on_off = "OFF"
    else:
        try:
            modbus_client.write_coil(0, False)
        except:
            traceback.print_exc()
    send_event_info()
        
@app.route('/settings', methods=['POST', 'GET'])
@flask_login.login_required
def route_settings():
    global settings, modbus_client
    if flask.request.method == 'POST':
        modified = False
        
        for k in settings.keys(): 
            if k in flask.request.form and settings[k]!=flask.request.form.get(k):
                settings[k]=flask.request.form.get(k)
                modified = True
        
        if modified:
            with open(settings_file, "wt") as f:
                json.dump(settings, f, sort_keys=True, indent=4)
                
            # Restart MODBUS client
            if modbus_client:   
                modbus_client.close()
            modbus_client = ModbusTcpClient(settings["ip_address"])
 
    return flask.render_template('settings.html', 
                **settings)
                    
# somewhere to login
@app.route("/login", methods=["GET", "POST"])
def route_login():
    if flask.request.method == 'POST':
        if ((flask.request.form['username']==settings['username']) and
            (flask.request.form['password']==settings['password'])):        
            user = User(0)
            flask_login.login_user(user)
            return flask.redirect(flask.request.args.get("next"))
        else:
            return flask.abort(401)
    else:
        return flask.render_template('login.html')

# somewhere to logout
@app.route("/logout")
@flask_login.login_required
def route_logout():
    flask_login.logout_user()
    return flask.redirect('/')


# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return flask.render_template('login.html', login_failed=True)
    
# callback to reload the user object        
@login_manager.user_loader
def load_user(userid):
    return User(userid)
    
    
# Serve the UI        
@app.route('/zone<n>')
def zone_control(n):
    try:
        zone_title = settings['zone_title' + str(n)]
    except KeyError:
        zone_title = "Zone " + str(n)
    return flask.render_template("illuminate.html", zone_number=n, zone_title=zone_title)

@app.route("/")
def default_zone():
    return zone_control("1")
    
def run_illuminate(debug=False):
    global DEBUG, modbus_client
    DEBUG = debug
    load_settings()
    
    # Start Modbus Client
    modbus_client = ModbusTcpClient(settings["ip_address"])
    # Start webserver
    socketio.run(app, host="0.0.0.0")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Web control for MODBUS/PowerLink devices.')
    parser.add_argument('--debug', '-d', action = 'store_const', const=True, default = False,
        help='Display debug info at console')
    args = parser.parse_args()

    try:
        run_illuminate(debug = args.debug)
    except:
        traceback.print_exc()
    finally:
        input('Press enter to continue...')
        