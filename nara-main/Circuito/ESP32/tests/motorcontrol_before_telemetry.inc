void callback_motorcontrol(){
    input_left  = newLeft  / dt;
    input_right = newRight / dt;
    setpoint_left  = targetleftVel;
    setpoint_right = targetrightVel;

    pidLeft.Compute();   
    pidRight.Compute();

    // ====================================================================
    // ZONA MORTA DINÂMICA INDEPENDENTE (Compensação de Assimetria)
    
    float DEADBAND_LEFT = 20;  
    float DEADBAND_RIGHT = 22.5; 

    float final_pwm_left = output_left;
    float final_pwm_right = output_right;
    //float final_pwm_left = 60.0;
    //float final_pwm_right = 60.0;

    // Compensação da Roda Esquerda
    
    if (setpoint_left > 0.05 && output_left < DEADBAND_LEFT && output_left > 0) {
        final_pwm_left = DEADBAND_LEFT;
    } else if (setpoint_left < -0.05 && output_left > -DEADBAND_LEFT && output_left < 0) {
        final_pwm_left = -DEADBAND_LEFT;
    }

    // Compensação da Roda Direita (O motor problemático)
    if (setpoint_right > 0.05 && output_right < DEADBAND_RIGHT && output_right > 0) {
        final_pwm_right = DEADBAND_RIGHT;
    } else if (setpoint_right < -0.05 && output_right > -DEADBAND_RIGHT && output_right < 0) {
        final_pwm_right = -DEADBAND_RIGHT;
    }
    
    // Desliga totalmente se o alvo for zero (Segurança)
    if (fabs(setpoint_left) < 0.01) final_pwm_left = 0.0;
    if (fabs(setpoint_right) < 0.01) final_pwm_right = 0.0;
    // ====================================================================

    // Motor direito (Usando o PWM compensado)
    if(final_pwm_right >= 0){
      mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A);
      mcpwm_set_duty(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B, final_pwm_right);
      mcpwm_set_duty_type(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B, MCPWM_DUTY_MODE_0);
    } else {
      mcpwm_set_signal_low(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_B);
      mcpwm_set_duty(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A, fabs(final_pwm_right));
      mcpwm_set_duty_type(MCPWM_UNIT_1, MCPWM_TIMER_0, MCPWM_GEN_A, MCPWM_DUTY_MODE_0);
    }

    // Motor esquerdo (Usando o PWM compensado)
    if(final_pwm_left >= 0){
      mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A);
      mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B, final_pwm_left);
      mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B, MCPWM_DUTY_MODE_0);
    } else {
      mcpwm_set_signal_low(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_B);
      mcpwm_set_duty(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A, fabs(final_pwm_left));
      mcpwm_set_duty_type(MCPWM_UNIT_0, MCPWM_TIMER_0, MCPWM_GEN_A, MCPWM_DUTY_MODE_0);
    }
}
