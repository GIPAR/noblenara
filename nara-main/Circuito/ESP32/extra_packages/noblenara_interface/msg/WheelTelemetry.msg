# Snapshot do ciclo de controle. Arrays: [esquerda, direita].
uint8 LEFT=0
uint8 RIGHT=1
uint8 SCHEMA_VERSION=1

# Mesmo instante da leitura dos encoders deste ciclo, na epoca micro-ROS.
builtin_interfaces/Time stamp
uint32 sequence
uint32 uptime_ms
uint32 command_age_ms
bool command_received
bool watchdog_active
bool time_synchronized

float32 control_dt_s
# Inclui publicacoes e controle; a duracao completa e a do ciclo anterior.
uint32 previous_cycle_duration_us
uint32 cycle_duration_before_telemetry_us
uint32 telemetry_publish_failures

# Ultimo comando recebido; pode estar vencido. Consultar watchdog_active.
float32 command_linear_mps
float32 command_angular_radps

# Alvos efetivos depois do watchdog; sinais seguem o firmware dos motores.
float32[2] target_mps
float32[2] measured_mps
float32[2] error_mps
float32[2] pid_output_pct
float32[2] applied_pwm_pct
float32[2] p_term_pct
# GetIterm e a contribuicao integral incremental da QuickPID.
# output_sum inclui o acumulador interno: nao interpretar i_term isoladamente.
float32[2] i_term_pct
float32[2] d_term_pct
float32[2] output_sum_pct
float32[2] kp
float32[2] ki
float32[2] kd
bool[2] minimum_pwm_applied
bool[2] zero_target_override
bool[2] pid_at_output_limit
