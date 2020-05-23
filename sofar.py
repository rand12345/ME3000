from flask import Flask, render_template
import sys

sys.path.insert(0, '/home/pi/ME3000')
import me3000 as me

app = Flask(__name__)
def MyConfiguration():
    file = 'agile.cfg')
    parser = configparser.ConfigParser()
    parser.optionxform = str  # make option names case sensitive
    found = parser.read(file)
    if not found:
        raise ValueError('No config file found!')
    return parser

cfg = MyConfiguration()

def read_threshold():
    return  int(cfg['sofar']['threshold'])


def write_threshold(pctval):
    if pctval >=20 and pctval <= 100:
        try:
            config.set ('sofar', 'threshold', str(pctval))
            with open ('agile.cfg', 'w') as configfile:
                config.write (configfile)
            return pctval
        except:
            return -1
    else:
        return -1


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/pct/')
@app.route('/pct/<int:pct_val>')
def set_pct(pct_val=None):
    if pct_val == None:
        retval = read_threshold()
        if retval != -1:
            return render_template('pct.html', opstr="Current", pctval=retval) 
        else:
            return render_template('error.html'), 500
    else:
        retval = write_threshold(pct_val)
        if retval != -1:
            return render_template('pct.html', opstr="New", pctval=retval) 
        else:
            return render_template('error.html'), 500
    
    
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

