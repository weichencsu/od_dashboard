import streamlit as st 
import numpy as np 
import mrlcpower
import plotly.graph_objects as go

def pieChart(labels, values):
    # Add histogram data
    fig = go.Figure()
    #config = {'displayModeBar': False}
    fig.add_trace(go.Pie(labels=labels, values=values))

    fig.update_layout(
        autosize=False,
        margin=dict(l=1, r=1, t=1, b=1)
    )

    fig.update_layout(
        showlegend=True,
        font=dict(
            family="Ubuntu, regular",
            size=12,
            color="Black"
        )
    )

    fig.update_layout(legend=dict(
    yanchor="top",
    y=0.97,
    xanchor="left",
    x=0.03
    ))

    return fig


def PREDICT_TOTAL_CHARGE(actualDia, bellyLen, centreLen, trinionDia, coneLen, speed, millSizeNum, oreSG, ballSG, totalPower, ballFill, overflowFlag, gearedFlag):
    results = []
    for tc in np.arange(0.1, 0.55, 0.0001):
            noLoadP_TMP, shellPower_TMP, conicalPower_TMP, totalPowerkW_TMP = mrlcpower.millPower(actualDia, bellyLen, centreLen, trinionDia, coneLen, speed, millSizeNum, oreSG, ballSG, tc, ballFill, overflowFlag, gearedFlag)
            
            diff = abs(totalPowerkW_TMP - totalPower)
            if diff < 3.0:
                results.append(tc)
    #print(results)
    if results:
        return results[0]
    else:
        return 0



def checkinput(millIntDia, plateWear, bellyLen, trinionDia, coneLen, oreSG, totalFill, speed):
    if millIntDia and plateWear and bellyLen and trinionDia and coneLen and oreSG and totalFill and speed:
        return True
    else:
        return False

def app():
    st.header("""
            Mill Power Draw Prediction and Mill Filling Estimation
            """, divider = 'rainbow')

    # section 1: 
    st.subheader("1. Mill Power Draw Prediction")
    #st.markdown("###")
    # add opetions
    predictionOption = st.container()
    with predictionOption:
        coll1, coll2 = st.columns(2)
        with coll1:
            calcType = st.radio(
            "1. Please Select Calculation Mode",
            ('From Total Filling to Power Draw', 'From Power Draw to Total Filling'))
        with coll2:
            millSelect = st.radio(
            "2. Please Select Grinding Mills",
            ('34FT - Fuller', '38FT - Svedala'))


    #st.markdown("###")
    #st.markdown("---")
    st.subheader("1.1 Run Calculation")
    pdContainer = st.container()
    with pdContainer:
        col1, col2, col3 = st.columns([1, 1, 2], vertical_alignment="top", border=True)
        with col1:
            millType = 'AG'
            st.text_input(
            'Mill Type is: ',
            'AG Mill')
            if millSelect == "34FT - Fuller":            
                millSize = st.text_input(
                'Mill Size is: ',
                '34FT')
                millIntDia = st.text_input('Mill Internal Diameter - m', '10.37', help="The radius should calculate from the mill centre to the top of the shell plate! Please use 9.5712m")
                plateWear = st.text_input('Percentage of Liner Wear - %', '0', help="Liner wear precentage, ranging from 0 ~ 100")
                bellyLen = st.text_input('Cylindrical Section Length - m', '4.772', help="This is the cylindrical section length inside liners! Please use 4.772m")
                centreLen = st.text_input('Mill Centre Line Length - m', '7.733', help="This is centre line length inside liners within the mill! Please use 7.733m")
                trinionDia = st.text_input('Mill Trunnion Diameter - m', '2.636', help="This is discharge trunion diameter of the mill! Please use 2.636m")
                coneLen = st.text_input('Conical Section Length - m', '1.066', help="This is estimated conical section length! Please use 1.066m")
            else:
                millSize = st.text_input(
                'Mill Size is: ',
                '38FT')
                millIntDia = st.text_input('Mill Internal Diameter - m', '11.3733', help="The radius should calculate from the mill centre to the top of the shell plate! Please use 11.3733m")
                plateWear = st.text_input('Percentage of Liner Wear - %', '0', help="Liner wear precentage, ranging from 0 ~ 100")
                bellyLen = st.text_input('Cylindrical Section Length - m', '6.665', help="This is the cylindrical section length inside liners! Please use 6.665m")
                centreLen = st.text_input('Mill Centre Line Length - m', '11.444', help="This is centre line length inside liners within the mill! Please use 11.444m")
                trinionDia = st.text_input('Mill Trunnion Diameter - m', '2.6', help="This is discharge trunion diameter of the mill! Please use 2.6m")
                coneLen = st.text_input('Conical Section Length - m', '1.58', help="This is estimated conical section length! Please use 1.58m")
            #millSize = st.selectbox(
            #'Please Select Mill Size',
            #('38FT', '24FT', '26FT', '28FT', '30FT', '32FT', '34FT', '36FT', '40FT'))
            millSizeNum = millSize[0:2]
            

        with col2:
            # get all flags
            ballSGDisable = False
            ballFillDisable = False
            if millType == 'AG':
                ballSGDisable = True
                ballFillDisable = True
            # inputs
            oreSG = st.text_input('Ore Density - t/m³', '')
            ballSG = st.text_input('Ball Density - t/m³', '7.85', disabled = ballSGDisable)
            if calcType == 'From Total Filling to Power Draw':
                totalFill = st.text_input('Total Filling - %', '', help="Ball filling is Total Filling for Ball Mill Power Draw Prediction")
            else:
                totalPower = st.text_input('Total Power Draw - kW', '', help="The total power draw consumed by the mill in kW")
            ballFill = st.text_input('Ball Filling - %', '', help="Ball filling is Total Filling for Ball Mill Power Draw Prediction", disabled = ballFillDisable)
            if ballFillDisable and ballSGDisable:
                ballFill = 0
                ballSG = 0
            speed = st.text_input('Mill Speed - RPM', '')
            dischargeType = st.radio(
                "Please Select Discharge Type",
                ('Overflow', 'Grate')) 
            if dischargeType == 'Overflow':
                overflowFlag = True
            else:
                overflowFlag = False
                
            millDrive = st.radio(
                "Please Select Mill Drive Type",
                ('Gear and Pinion', 'Gearless')) 
            if millDrive == 'Gear and Pinion':
                gearedFlag = True
            else:
                gearedFlag = False

            calcPressed = st.button("Calculate")
        
        with col3:
            if calcType == 'From Total Filling to Power Draw':
                drivePower = 0
                conicalPower = 0
                shellPower = 0
                totalPower = 0
                if calcPressed:
                    calcFlag = checkinput(millIntDia, plateWear, bellyLen, trinionDia, coneLen, oreSG, totalFill, speed)
                    if calcFlag:
                        actualDia = float(millIntDia)+float(plateWear)/500
                        #print(actualDia)
                        noLoadP, shellPower, conicalPower, totalPowerkW = mrlcpower.millPower(actualDia, float(bellyLen), float(centreLen), float(trinionDia), float(coneLen), float(speed), float(millSizeNum), float(oreSG), float(ballSG), float(totalFill)/100, float(ballFill)/100, overflowFlag, gearedFlag)
                        drivePower = noLoadP
                        conicalPower = conicalPower
                        shellPower = shellPower
                        totalPower = totalPowerkW
                    else:
                        st.error("Input paramters are either not complete or wrong, please check again!!!")
                st.metric(label="Predicted no-load Draw - [kW]", value=round(drivePower, 1))
                st.metric(label="Predicted Power from Shell - [kW]", value=round(shellPower, 1))
                st.metric(label="Predicted Power from Conical Section - [kW]", value=round(conicalPower, 1))
                st.metric(label="Predicted Total Power Draw - [kW]", value=round(totalPower, 1))
                fig = pieChart(['No-load Power', 'Cylindrical Section Power', 'Conical Section Power'], [drivePower, shellPower, conicalPower])
                st.plotly_chart(fig, use_container_width=True)
            else:
                predicted_charge = 0
                if calcPressed:
                    calcFlag = checkinput(millIntDia, plateWear, bellyLen, trinionDia, coneLen, oreSG, totalPower, speed)
                    if calcFlag:
                        actualDia = float(millIntDia)+float(plateWear)/500
                        predicted_charge = PREDICT_TOTAL_CHARGE(actualDia, float(bellyLen), float(centreLen), float(trinionDia), float(coneLen), float(speed), float(millSizeNum), float(oreSG), float(ballSG), float(totalPower), float(ballFill)/100, overflowFlag, gearedFlag)
                        if predicted_charge == 0:
                            st.markdown("###")
                            st.error("The predicted charge level is outside 0.1 ~ 0.5 range, please double check your input!")
                    else:
                        st.error("Input paramters are either not complete or wrong, please check again!!!")
                
                st.metric(label="Predicted Total Filling - [%]", value = round(predicted_charge*100, 2))

    # section 2: 
    st.subheader("1.2 Mill Filling Estimation")

    millSelect = st.radio(
        "1. Please Select Grinding Mills",
        ('34FT - Fuller', '38FT - Svedala'))

    chargeLevels38 = [2.26, 
                    2.77, 
                    3.36, 
                    3.99, 
                    4.63, 
                    5.33, 
                    6.04, 
                    6.78, 
                    7.54, 
                    8.30, 
                    9.09, 
                    9.96, 
                    10.80, 
                    11.67, 
                    12.54, 
                    13.42, 
                    14.32, 
                    15.23, 
                    16.24, 
                    17.20, 
                    18.17, 
                    19.14, 
                    20.12, 
                    21.11, 
                    22.19, 
                    23.23, 
                    24.27, 
                    25.31, 
                    26.35, 
                    27.40, 
                    28.46, 
                    29.61, 
                    30.71, 
                    31.80, 
                    32.90, 
                    33.99, 
                    35.09, 
                    36.29, 
                    37.40, 
                    38.52, 
                    39.66, 
                    40.80, 
                    41.92, 
                    43.05, 
                    44.28, 
                    45.41, 
                    46.54, 
                    47.69, 
                    48.85, 
                    50.00]

    chargeLevels34 = [2.86, 
                    3.57, 
                    4.30, 
                    5.01, 
                    5.77, 
                    6.61, 
                    7.47, 
                    8.34, 
                    9.21, 
                    10.06, 
                    11.01, 
                    12.06, 
                    13.07, 
                    14.08, 
                    15.08, 
                    16.05, 
                    17.13, 
                    18.30, 
                    19.41, 
                    20.54, 
                    21.65, 
                    22.73, 
                    23.81, 
                    25.02, 
                    26.29, 
                    27.48, 
                    28.69, 
                    29.88, 
                    31.04, 
                    32.20, 
                    33.56, 
                    34.79, 
                    36.04, 
                    37.30, 
                    38.56, 
                    39.78, 
                    40.98, 
                    42.33, 
                    43.61, 
                    44.89,
                    46.16, 
                    47.45, 
                    48.73]

    millCharge = st.container()
    with millCharge:
        col1, col2 = st.columns([1, 1], vertical_alignment="top", border=True)
        with col1:
            if millSelect == "34FT - Fuller":
                st.info("🚩  Shell liner profile has been updated with the latest profile from scan.")
                #st.markdown("###")
                st.info("🚩  The total charge level is estimated based on the shell cross-sectional area.")
                #st.markdown("###")
                st.success("🚩  You have selected " + millSelect)
                st.markdown("###")
                chargeLvOpt = st.select_slider('2. Please Select Total Charge Level - %', 
                                            options=chargeLevels34, value=chargeLevels34[int(len(chargeLevels34)/2-1)])
                st.markdown("###")
                #st.markdown("Coming soon: Power Draw as an indicator for Mill Filling")
            else:
                st.info("🚩  Shell liner profile has been updated with the latest profile from scan.")
                #st.markdown("###")
                st.info("🚩  The total charge level is estimated based on the shell cross-sectional area.")
                #st.markdown("###")
                st.success("🚩  You have selected " + millSelect)
                st.markdown("###")
                chargeLvOpt = st.select_slider('2. Please Select Total Charge Level - %', 
                                            options=chargeLevels38, value=chargeLevels38[int(len(chargeLevels38)/2-1)])
                st.markdown("###")



        with col2:
            if millSelect == "34FT - Fuller":
                st.session_state.chargeid = chargeLevels34.index(chargeLvOpt)
                imgName = "Charge/Fuller/charge_" + str(st.session_state.chargeid) + ".png"
                captionName = "Estimated charge level is:" + str(chargeLvOpt) + "%"
                st.image(imgName, caption=captionName, use_container_width=True)
            else:
                st.session_state.chargeid = chargeLevels38.index(chargeLvOpt)
                imgName = "Charge/charge_" + str(st.session_state.chargeid) + ".png"
                captionName = "Estimated charge level is:" + str(chargeLvOpt) + "%"
                st.image(imgName, caption=captionName, use_container_width=True)

###############################################################################
    #st.subheader("2. Time Series Mill Filling")

