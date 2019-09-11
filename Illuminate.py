#! /usr/bin/python3
import flask
import flask_login
import flask_socketio
import traceback
import json
import os.path
import glob


DEBUG = False
#DEBUG = True
settings_file = './settings.json'
main_thread = None

temp_on_off = 'OFF'

settings = {
    'ip_address': '192.168.1.1',
    'tcp_port': 504,
    'username': 'admin',
    'password': 'password'
    }


app = flask.Flask(__name__)
# config
app.config.update(
    DEBUG = False,
    SECRET_KEY = 'rimnqiuqnewiornhf7nfwenjmqvliwynhtmlfnlsklrmqwe'
)
socketio = flask_socketio.SocketIO(app)


def load_settings():
    global settings
    try:
        with open(settings_file, "rt") as f:
            settings.update(json.load(f))
    except: pass

def send_event_info():
    socketio.emit('update', {"zone1_status": temp_on_off}, namespace='/ws/zone1')

def main_thread_worker():
    while True:
        send_event_info()
        socketio.sleep(2.0)    
            
# flask-login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "route_login"

# simple user model
class User(flask_login.UserMixin):
    def __init__(self, id):
        self.id = id
        self.name = settings['username']
        self.password = settings['password']
        
    def __repr__(self):
        return "%d/%s" % (self.id, self.name)


# create the user       
user = User(0)
            
@socketio.on('connect', namespace='/ws/zone1')
def ws_connect():
    global main_thread
    if(main_thread is None):
        main_thread = socketio.start_background_task(target=main_thread_worker)
        
    send_event_info()

@socketio.on('turn_on', namespace='/ws/zone1')
def ws_turn_on(d):
    global temp_on_off
    temp_on_off = "ON"
    send_event_info()

@socketio.on('turn_off', namespace='/ws/zone1')
def ws_turn_on(d):
    global temp_on_off
    temp_on_off = "OFF"
    send_event_info()

        
@app.route('/settings', methods=['POST', 'GET'])
@flask_login.login_required
def route_settings():
    global settings
    if flask.request.method == 'POST':
        modified = False
        
        for k in settings.keys(): 
            if k in flask.request.form and settings[k]!=flask.request.form.get(k):
                settings[k]=flask.request.form.get(k)
                modified = True
        
        if modified:
            with open(settings_file, "wt") as f:
                json.dump(settings, f, sort_keys=True, indent=4)
 
    return flask.render_template('settings.html', 
                ip_address=settings['ip_address'], 
                tcp_port=settings['tcp_port'],
                user_name=settings['username'])
                    
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
    return flask.render_template("illuminate.html", zone_number=zone_number)

@app.route("/")
def default_zone():
    return flask.render_template("illuminate.html", zone_number="1")

if __name__ == '__main__':
    import argparse
    
    load_settings()

    parser = argparse.ArgumentParser(description='Provide HTML rendering of Coloado Timing System data.')
    parser.add_argument('--port', '-p', action = 'store', default = '', 
        help='Serial port input from CTS scoreboard')
    parser.add_argument('--in', '-i', action = 'store', default = '', dest='in_file',
        help='Input file to use instead of serial port')
    parser.add_argument('--out', '-o', action = 'store', default = '', 
        help='Output file to dump data')
    parser.add_argument('--portlist', '-l', action = 'store_const', const=True, default = False,
        help='List of available serial ports')        
    parser.add_argument('--speed', '-s', action = 'store', default = 1.0, dest='in_speed',
        help='Speed to play input file at')
    parser.add_argument('--debug', '-d', action = 'store_const', const=True, default = False,
        help='Display debug info at console')
    args = parser.parse_args()

    try:
        debug_console = args.debug
        socketio.run(app, host="0.0.0.0")
    except:
        traceback.print_exc()
    finally:
        input('Press enter to continue...')
        