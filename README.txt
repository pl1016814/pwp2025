In the PCA9685.py file, change "self.bus = smbus3.SMBus(1)" to "self.bus = smbus.SMBus(1)" (without the 3).

Put these commands in terminal of the robot:
cd ~/robot
uvicorn apiWaveshare:app --host 0.0.0.0 --port 8000
pip install fastapi "uvicorn[standard]" pydantic requests
setx ROBOT_BASE "http://192.168.240.17:8000"

Then put this commands in the terminal of the computer of the webserver:
uvicorn api:app --host 0.0.0.0 --port 8080

Then add this line to the GUI code:
"const BASE = "http://192.168.240.42:8080";"
Replace "const BASE = "http://192.168.240.42:8080";" with the IP of the webserver computer.
