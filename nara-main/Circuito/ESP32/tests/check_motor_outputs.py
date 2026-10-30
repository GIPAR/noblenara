#!/usr/bin/env python3
"""Compara chamadas MCPWM antes/depois da instrumentacao; sem hardware."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/main.cpp").read_text()
start = source.index("void callback_motorcontrol(){")
after = source[start:source.index("\n}", start) + 2]
before = (ROOT / "tests/motorcontrol_before_telemetry.inc").read_text()

stub = r'''
std::vector<std::array<float, 5>> calls;
constexpr int MCPWM_UNIT_0=0, MCPWM_UNIT_1=1, MCPWM_TIMER_0=0;
constexpr int MCPWM_GEN_A=0, MCPWM_GEN_B=1, MCPWM_DUTY_MODE_0=0;
constexpr float PWM_MAX=100;
void mcpwm_set_signal_low(int u,int t,int g){calls.push_back({0,float(u),float(t),float(g),0});}
void mcpwm_set_duty(int u,int t,int g,float v){calls.push_back({1,float(u),float(t),float(g),v});}
void mcpwm_set_duty_type(int u,int t,int g,int v){calls.push_back({2,float(u),float(t),float(g),float(v)});}
double newLeft=0, newRight=0, targetleftVel=0, targetrightVel=0;
float dt=.02f, input_left=0, input_right=0, setpoint_left=0, setpoint_right=0;
float output_left=0, output_right=0;
// O PID nao mudou: injetar suas saidas para exercitar compensacao e GPIOs.
struct PID {
 void Compute(){}
 float GetPterm(){return 1;} float GetIterm(){return 2;}
 float GetDterm(){return 3;} float GetOutputSum(){return 4;}
 float GetKp(){return 25;} float GetKi(){return 30;} float GetKd(){return 0;}
} pidLeft, pidRight;
'''
telemetry = ["target_mps", "measured_mps", "error_mps", "pid_output_pct",
             "applied_pwm_pct", "p_term_pct", "i_term_pct", "d_term_pct",
             "output_sum_pct", "kp", "ki", "kd", "minimum_pwm_applied",
             "zero_target_override", "pid_at_output_limit"]
struct = "struct Telemetry {" + "".join(f"float {field}[2]={{}};" for field in telemetry) + "} wheel_telemetry_msg;"
program = "#include <array>\n#include <vector>\n#include <cmath>\n#include <cassert>\n#include <iostream>\n"
program += "namespace original {\n" + stub + before + "\n}\n"
program += "namespace instrumented {\n" + stub + struct + after + "\n}\n"
program += r'''
int main(){
 float targets[]={-.3f,-.051f,-.05f,-.049f,-.011f,-.01f,-.009f,0,.009f,.01f,.011f,.049f,.05f,.051f,.3f};
 float outputs[]={-100,-22.6f,-22.5f,-20,-19.9f,-.1f,0,.1f,19.9f,20,22.5f,22.6f,100};
 unsigned count=0;
 for(float left:targets) for(float right:targets)
 for(float pl:outputs) for(float pr:outputs){
  original::targetleftVel=instrumented::targetleftVel=left;
  original::targetrightVel=instrumented::targetrightVel=right;
  original::output_left=instrumented::output_left=pl;
  original::output_right=instrumented::output_right=pr;
  original::newLeft=instrumented::newLeft=.001;
  original::newRight=instrumented::newRight=-.002;
  original::calls.clear(); instrumented::calls.clear();
  original::callback_motorcontrol(); instrumented::callback_motorcontrol();
  assert(original::calls==instrumented::calls);
  auto &m=instrumented::wheel_telemetry_msg;
  assert(m.target_mps[0]==left && m.target_mps[1]==right);
  assert(m.pid_output_pct[0]==pl && m.pid_output_pct[1]==pr);
  assert(m.zero_target_override[0]==(std::fabs(left)<.01));
  assert(m.zero_target_override[1]==(std::fabs(right)<.01));
  assert(m.pid_at_output_limit[0]==(std::fabs(pl)>=100));
  assert(m.pid_at_output_limit[1]==(std::fabs(pr)>=100));
  // A segunda e a quinta chamadas definem duty direita/esquerda.
  assert(std::fabs(m.applied_pwm_pct[1])==instrumented::calls[1][4]);
  assert(std::fabs(m.applied_pwm_pct[0])==instrumented::calls[4][4]);
  ++count;
 }
 std::cout << count << " combinacoes: chamadas MCPWM identicas e snapshot coerente\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory)
    (path / "test.cpp").write_text(program)
    subprocess.run(["g++", "-std=c++17", "-O2", str(path / "test.cpp"), "-o", str(path / "test")], check=True)
    subprocess.run([str(path / "test")], check=True)
