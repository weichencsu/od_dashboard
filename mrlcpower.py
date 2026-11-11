import math
def criticalSpeed(speed, millSizeFT):
    criticalSpeed100 = 76.6*pow(millSizeFT, -0.5)
    criticalSpeedResult = speed/criticalSpeed100
    return criticalSpeedResult

def noLoadPower(gearedFlag, diameter, criticalSpeedResult, bellyLen, coneLen):
    if gearedFlag:
        K = 1.68
    else:
        K = 1.0
    pTMP1 = K*pow(diameter, 2.05)
    pTMP2 = 0.667*coneLen+bellyLen
    pTMP3 = pow(criticalSpeedResult*pTMP2, 0.82)
    return pTMP1*pTMP3

def chargeDensity(oreSG, ballSG, ballFill, millFill):
    chargeDensityTMP1 = 0.8*oreSG
    chargeDensityTMP2 = (ballSG - oreSG)*0.6*ballFill/millFill
    return chargeDensityTMP1+chargeDensityTMP2+0.2

def calcToeSlurryShoulderAngles(criticalSpeedResult, millFill):
    # calc phi_c
    phiCOMP = 0.35*(3.364-millFill)
    if criticalSpeedResult > phiCOMP:
        phi_c = criticalSpeedResult
    else:
        phi_c = phiCOMP
    # calc phi_T
    phi_T_tmp1 = 2.5307*(1.2796-millFill)
    phi_T_tmp2 = math.exp(-19.42*(phi_c-criticalSpeedResult))
    phi_T_tmp3 = math.pi/2
    phi_T = phi_T_tmp1*(1-phi_T_tmp2) + phi_T_tmp3
    # calc phi_TO
    phi_TO = 3.395
    # calc theta_s
    theta_s_tmp1 = (phi_T-phi_T_tmp3)
    theta_s_tmp2 = 0.3386+0.1041*criticalSpeedResult+(1.54-2.5673*criticalSpeedResult)*millFill
    theta_s = phi_T_tmp3-theta_s_tmp1*theta_s_tmp2
    return phi_c, phi_T, phi_TO, theta_s

def calcInnerSurfRad(speed, diameter, millFill, phi_T, theta_s):
    # calc t_c
    N_dash = speed/120
    t_c = (2*math.pi-phi_T+theta_s)/(2*math.pi*N_dash)
    # r-dash
    r_dash_tmp1 = diameter/4
    r_dash_tmp2 = math.pi*2*millFill/(math.pi*2+theta_s-phi_T)
    r_dash_tmp3 = pow(1-r_dash_tmp2, 0.5)
    r_dash = r_dash_tmp1*(1+r_dash_tmp3)
    # calc t_f
    t_f_tmp1 = 2*r_dash*(math.sin(theta_s) - math.sin(phi_T))/9.81
    t_f = pow(t_f_tmp1, 0.5)
    # calc beta
    beta = t_c/(t_c+t_f)
    # calc r_i
    r_i_tmp1 = 2*math.pi*beta*millFill/(2*math.pi+theta_s-phi_T)
    r_i = diameter/2*pow(1-r_i_tmp1, 0.5)
    return t_c, t_f, r_i

def calcPowerShell(millFill, bellyLen, speed, diameter, pulpDen, rhoCharge, theta_s, phi_T, r_i, phi_TO):
    # calc z
    z = pow(1-millFill, 0.4532)
    #print(z)
    p1 = math.pi*9.81*bellyLen*(speed/60)*(diameter/2)/3/(diameter/2-z*r_i)
    #print(p1)
    p2 = 2*pow(diameter/2, 3) - 3*z*pow(diameter/2, 2)*r_i + pow(r_i, 3)*(3*z-2)
    #print(p2)
    p3 = rhoCharge*(math.sin(theta_s) - math.sin(phi_T)) + pulpDen*(math.sin(phi_T) - math.sin(phi_TO))
    #print(p3)
    pp4 = (speed/60)*(diameter/2)*math.pi/((diameter/2)-z*r_i)
    p4 = bellyLen*rhoCharge*pow(pp4, 3)
    #print(p4)
    p5 = pow(((diameter/2)-z*r_i), 4) - pow(r_i, 4)*pow(z-1, 4)
    #print(p5)
    powerShell = p1*p2*p3 + p4*p5
    return powerShell

def calcConicalPower(coneLen, speed, diameter, tronionDia, r_i, rhoCharge, theta_s, phi_T, phi_TO, pulpDen):
    p1 = math.pi*coneLen*9.81*(speed/60)/3/(diameter/2-tronionDia/2)
    p2 = pow(diameter/2, 4) - 4*(diameter/2)*pow(r_i, 3) + 3*pow(r_i, 4)
    p3 = rhoCharge*(math.sin(theta_s) - math.sin(phi_T)) + pulpDen*(math.sin(phi_T) - math.sin(phi_TO))
    p4 = pow(math.pi,3)*2*pow(speed/60,3)*coneLen*rhoCharge/5/(diameter/2-tronionDia/2)
    p5 = pow(diameter/2, 5) - 5*(diameter/2)*pow(r_i, 4) + 4*pow(r_i, 5)
    conicalPower = p1*p2*p3+p4*p5
    return conicalPower

def millPower(diameter, bellyLen, centreLen, tronionDia, coneLen, speed, millSizeFT, oreSG, ballSG, millFill, ballFill, overflowFlag, gearedFlag):
    if overflowFlag:
        pulpDen = 0.495
    else:
        pulpDen = 0.0

    # 1. calc critical speed
    criticalSpeedResult = criticalSpeed(speed, millSizeFT)
    # 2. calc noload power
    noLoadP = noLoadPower(gearedFlag, diameter, criticalSpeedResult, bellyLen, coneLen)
    # 3. calc rhoCharge
    rhoCharge = chargeDensity(oreSG, ballSG, ballFill, millFill)
    # 4. calc toe, slurry toe, and shoulder angle
    phi_c, phi_T, phi_TO, theta_s = calcToeSlurryShoulderAngles(criticalSpeedResult, millFill)
    # 5. calc inner surface radius of charge
    t_c, t_f, r_i = calcInnerSurfRad(speed, diameter, millFill, phi_T, theta_s)
    # 6. calc shell power
    shellPower = calcPowerShell(millFill, bellyLen, speed, diameter, pulpDen, rhoCharge, theta_s, phi_T, r_i, phi_TO)
    # 7. calc conical power
    conicalPower = calcConicalPower(coneLen, speed, diameter, tronionDia, r_i, rhoCharge, theta_s, phi_T, phi_TO, pulpDen)
    # 8. calc total power
    totalPowerkW = noLoadP + (shellPower + conicalPower)*1.26
    return noLoadP, shellPower, conicalPower, totalPowerkW