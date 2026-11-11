import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
import os
import shutil
import numpy as np
import math

# --- Mill Power Calculation Functions (from mrlcpower) ---
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
    chargeDensityTMP1 = 0.763*oreSG
    chargeDensityTMP2 = (ballSG - oreSG)*0.635*ballFill/millFill
    return chargeDensityTMP1+chargeDensityTMP2+0.237

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
    p1 = math.pi*9.81*bellyLen*(speed/60)*(diameter/2)/3/(diameter/2-z*r_i)
    p2 = 2*pow(diameter/2, 3) - 3*z*pow(diameter/2, 2)*r_i + pow(r_i, 3)*(3*z-2)
    p3 = rhoCharge*(math.sin(theta_s) - math.sin(phi_T)) + pulpDen*(math.sin(phi_T) - math.sin(phi_TO))
    pp4 = (speed/60)*(diameter/2)*math.pi/((diameter/2)-z*r_i)
    p4 = bellyLen*rhoCharge*pow(pp4, 3)
    p5 = pow(((diameter/2)-z*r_i), 4) - pow(r_i, 4)*pow(z-1, 4)
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
    try:
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
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0, 0, 0, 0

# --- Mill Filling Calculation Function (from calcMillfing) ---
def PREDICT_TOTAL_CHARGE(actualDia, bellyLen, centreLen, trinionDia, coneLen, speed, millSizeNum, oreSG, ballSG, totalPower, ballFill, overflowFlag, gearedFlag):
    results = []
    try:
        for tc in np.arange(0.1, 0.55, 0.0001):
            noLoadP_TMP, shellPower_TMP, conicalPower_TMP, totalPowerkW_TMP = millPower(actualDia, bellyLen, centreLen, trinionDia, coneLen, speed, millSizeNum, oreSG, ballSG, tc, ballFill, overflowFlag, gearedFlag)
            
            # Skip if millPower returned zeros (indicating calculation error)
            if totalPowerkW_TMP == 0:
                continue
                
            diff = abs(totalPowerkW_TMP - totalPower)
            if diff < 3.0:
                results.append(tc)
        if results:
            return results[0]
        else:
            return 0
    except (ValueError, ZeroDivisionError, OverflowError):
        return 0

def checkinput(millIntDia, plateWear, bellyLen, trinionDia, coneLen, oreSG, totalFill, speed):
    if millIntDia and plateWear and bellyLen and trinionDia and coneLen and oreSG and totalFill and speed:
        return True
    else:
        return False

def calculate_mill_filling(df, power_col='POWER', rpm_col='RPM'):
    """Calculate mill filling for each row in dataframe"""
    
    # Mill constants
    millIntDia = 11.0
    plateWear = 100
    bellyLen = 6.665
    centreLen = 11.444
    trinionDia = 2.6
    coneLen = 1.58
    ballFill = 0
    ballSG = 0
    dischargeType = 'Grate'
    millDrive = 'Gear and Pinion'
    oreSG = 3.4
    actualDia = float(millIntDia) + float(plateWear)/500
    millSizeNum = 38
    overflowFlag = False
    gearedFlag = True
    
    mill_filling_values = []
    
    for idx, row in df.iterrows():
        try:
            # Get power and speed from the row
            totalPower = row[power_col]
            speed = row[rpm_col]
            
            # Skip if missing values
            if pd.isna(totalPower) or pd.isna(speed):
                mill_filling_values.append(0)
                continue
                
            # Skip if values are unreasonable
            if totalPower <= 0 or speed <= 0:
                mill_filling_values.append(0)
                continue
                
            # Calculate mill filling
            predicted_charge = PREDICT_TOTAL_CHARGE(
                actualDia, float(bellyLen), float(centreLen), float(trinionDia), 
                float(coneLen), float(speed), float(millSizeNum), float(oreSG), 
                float(ballSG), float(totalPower), float(ballFill)/100, 
                overflowFlag, gearedFlag
            )
            
            mill_filling_values.append(predicted_charge)
            
        except (ValueError, ZeroDivisionError, OverflowError, TypeError):
            mill_filling_values.append(0)
        except Exception:
            mill_filling_values.append(0)
    
    return mill_filling_values

def app():
    # --- Configuration ---
    DB_NAME = 'mill_data.db'
    TEMP_DB_NAME = 'mill_data_temp.db' # Temporary database name for reloading
    EXPECTED_FILES = {
        'svedala hourly data sep23_jun24.xlsx': ['Sheet1', 'Sheet2'], # SEP23, MAR24
        'Svedala Mill operating data 27 Sep 2024.xlsx': ['Sheet1'], # SEP24
        'Svedala Mill operating data 10 Mar 2025.xlsx': ['Sheet1'], # MAR25
        'Svedala Mill operating data 15 Sep 2025.xlsx': ['Sheet1']  # SEP25
    }
    st.subheader(":material/Factory: Svedala 38' AG Mill Performance Dashboard", divider = 'rainbow')
    st.markdown("""
    This application visualises AG mill operating data.
    It reads data from a local SQLite database (`mill_data.db`).
    If the database doesn't exist, it will be created from the Excel files in the current directory.
    """)

    # --- Check for Existing Database and Option to Reload ---
    db_exists = os.path.exists(DB_NAME)
    if db_exists:
        st.info(f"**Database `{DB_NAME}` found.**")
    else:
        st.info(f"**Database `{DB_NAME}` not found.** Attempting to load data from Excel files in the current directory...")

    # --- Data Preparation Section (Moved to Main Page) ---
    st.markdown("###")
    st.subheader(":material/Database:     Production Data Preparation", divider = 'gray')
    reload_data = st.checkbox("Reload data from Excel files?", value=False)

    # --- Database Setup/Reloading Logic ---
    if reload_data:
        st.info(f"**Reloading data process initiated.**")
        missing_files = []
        for filename in EXPECTED_FILES.keys():
            if not os.path.exists(filename):
                missing_files.append(filename)

        if missing_files:
            st.error(f"**Error: Required Excel files are missing:** {', '.join(missing_files)}")
            st.stop()

        # Load and process data from Excel files into a temporary database
        try:
            with st.spinner("Reloading data from Excel files into a new database..."):
                # Check if temp DB already exists and remove it
                if os.path.exists(TEMP_DB_NAME):
                    os.remove(TEMP_DB_NAME)
                    st.warning(f"Existing temporary database `{TEMP_DB_NAME}` removed.")

                conn = sqlite3.connect(TEMP_DB_NAME)

                # --- Load SEP23 and MAR24 from the combined file ---
                combined_file_path = 'svedala hourly data sep23_jun24.xlsx'
                xl_SEP23_MAR24 = pd.ExcelFile(combined_file_path)

                # Load SEP23 (Sheet1)
                df_SEP23 = pd.read_excel(xl_SEP23_MAR24, sheet_name='Sheet1', header=None, skiprows=1, nrows=3866, usecols="A:E")
                df_SEP23.columns = ['TIME', 'PEBBLE', 'POWER', 'FEED', 'SILICA']
                df_SEP23['TIME'] = pd.to_datetime(df_SEP23['TIME'], errors='coerce')
                df_SEP23 = df_SEP23[df_SEP23['TIME'].notna() & (df_SEP23['TIME'].dt.year != 1970)]
                df_SEP23['CUMFEED'] = df_SEP23['FEED'].cumsum()
                df_SEP23.to_sql('df_SEP23', conn, if_exists='replace', index=False)

                # Load MAR24 (Sheet2)
                df_MAR24 = pd.read_excel(xl_SEP23_MAR24, sheet_name='Sheet2', header=None, skiprows=1, nrows=1979, usecols="A:E")
                df_MAR24.columns = ['TIME', 'PEBBLE', 'POWER', 'FEED', 'SILICA']
                df_MAR24['TIME'] = pd.to_datetime(df_MAR24['TIME'], errors='coerce')
                df_MAR24 = df_MAR24[df_MAR24['TIME'].notna() & (df_MAR24['TIME'].dt.year != 1970)]
                df_MAR24['CUMFEED'] = df_MAR24['FEED'].cumsum()
                df_MAR24.to_sql('df_MAR24', conn, if_exists='replace', index=False)

                # --- Load SEP24 ---
                df_SEP24 = pd.read_excel('Svedala Mill operating data 27 Sep 2024.xlsx', sheet_name='Sheet1', header=None, skiprows=1, usecols="A:J")
                df_SEP24.columns = ['TIME', 'RPM', 'FEED', 'PEBBLE', 'WATER', 'SUMP', 'POWER', 'LOAD', 'DENSITY', 'SILICA']
                df_SEP24['TIME'] = pd.to_datetime(df_SEP24['TIME'], errors='coerce')
                df_SEP24 = df_SEP24[df_SEP24['TIME'].notna() & (df_SEP24['TIME'].dt.year != 1970)]
                threshold_date = pd.Timestamp("2024-10-01") # Example threshold if needed for SEP24
                # df_SEP24["FEED_REVISE"] = df_SEP24.apply(...) # Apply any required adjustments
                df_SEP24.set_index('TIME', inplace=True)
                df_SEP24 = df_SEP24.resample('H').mean()
                df_SEP24['CUMFEED'] = df_SEP24['FEED'].cumsum()
                
                # Calculate MILLFILLING for SEP24 and store in database
                with st.spinner("Calculating Mill Filling for SEP24..."):
                    df_SEP24['MILLFILLING'] = calculate_mill_filling(df_SEP24)
                
                # Reset index to store TIME as column for database
                df_SEP24_db = df_SEP24.reset_index()
                df_SEP24_db.to_sql('df_SEP24', conn, if_exists='replace', index=False)

                # --- Load MAR25 ---
                df_MAR25 = pd.read_excel('Svedala Mill operating data 10 Mar 2025.xlsx', sheet_name='Sheet1', header=None, skiprows=1, usecols="A:J")
                df_MAR25.columns = ['TIME', 'RPM', 'FEED', 'PEBBLE', 'WATER', 'SUMP', 'POWER', 'LOAD', 'DENSITY', 'SILICA']
                df_MAR25['TIME'] = pd.to_datetime(df_MAR25['TIME'], errors='coerce')
                df_MAR25 = df_MAR25[df_MAR25['TIME'].notna() & (df_MAR25['TIME'].dt.year != 1970)]
                threshold_date = pd.Timestamp("2025-04-06")
                df_MAR25["FEED_REVISE"] = df_MAR25.apply(
                    lambda row: row["FEED"] * 0.93 if row["TIME"] < threshold_date else row["FEED"], axis=1
                )
                df_MAR25.set_index('TIME', inplace=True)
                df_MAR25 = df_MAR25.resample('H').mean()
                df_MAR25['CUMFEED'] = df_MAR25['FEED'].cumsum()
                
                # Calculate MILLFILLING for MAR25 and store in database
                with st.spinner("Calculating Mill Filling for MAR25..."):
                    df_MAR25['MILLFILLING'] = calculate_mill_filling(df_MAR25)
                
                # Reset index to store TIME as column for database
                df_MAR25_db = df_MAR25.reset_index()
                df_MAR25_db.to_sql('df_MAR25', conn, if_exists='replace', index=False)

                # --- Load SEP25 ---
                df_SEP25 = pd.read_excel('Svedala Mill operating data 15 Sep 2025.xlsx', sheet_name='Sheet1', header=None, skiprows=1, usecols="A:J")
                df_SEP25.columns = ['TIME', 'RPM', 'FEED', 'PEBBLE', 'WATER', 'SUMP', 'POWER', 'LOAD', 'DENSITY', 'SILICA']
                df_SEP25['TIME'] = pd.to_datetime(df_SEP25['TIME'], errors='coerce')
                df_SEP25 = df_SEP25[df_SEP25['TIME'].notna() & (df_SEP25['TIME'].dt.year != 1970)]
                df_SEP25.set_index('TIME', inplace=True)
                df_SEP25 = df_SEP25.resample('H').mean()
                # Calculate MILL_AVAILABILITY
                mill_availability_values = []
                for i in range(len(df_SEP25)):
                    subset = df_SEP25.iloc[:i+1]
                    n = (subset['RPM'] >= 5).sum()
                    total_rows = len(subset)
                    mill_availability = (n / total_rows) * 100 if total_rows > 0 else 0
                    mill_availability_values.append(mill_availability)
                df_SEP25['MILL_AVAILABILITY'] = mill_availability_values
                df_SEP25['CUMFEED'] = df_SEP25['FEED'].cumsum()
                
                # Calculate MILLFILLING for SEP25 and store in database
                with st.spinner("Calculating Mill Filling for SEP25..."):
                    df_SEP25['MILLFILLING'] = calculate_mill_filling(df_SEP25)
                
                # Reset index to store TIME as column for database
                df_SEP25_db = df_SEP25.reset_index()
                df_SEP25_db.to_sql('df_SEP25', conn, if_exists='replace', index=False)

                conn.close()
                st.success(f"**Temporary database `{TEMP_DB_NAME}` created successfully from Excel files.**")

            # --- Swap Databases ---
            # Remove the old main database
            if os.path.exists(DB_NAME):
                os.remove(DB_NAME)
            # Rename the temporary database to the main database name
            shutil.move(TEMP_DB_NAME, DB_NAME)
            st.success(f"New database `{TEMP_DB_NAME}` renamed to `{DB_NAME}` and is now active.")

            # Reload the data from the newly renamed main database
            st.info(f"**Database reloaded successfully. Loading data from `{DB_NAME}`...**")
            conn = sqlite3.connect(DB_NAME)
            df_SEP23 = pd.read_sql_query("SELECT * FROM df_SEP23", conn)
            df_MAR24 = pd.read_sql_query("SELECT * FROM df_MAR24", conn)
            df_SEP24 = pd.read_sql_query("SELECT * FROM df_SEP24", conn)
            df_MAR25 = pd.read_sql_query("SELECT * FROM df_MAR25", conn)
            df_SEP25 = pd.read_sql_query("SELECT * FROM df_SEP25", conn)
            conn.close()

            # Convert TIME columns back to datetime after reading from DB
            df_SEP23['TIME'] = pd.to_datetime(df_SEP23['TIME'])
            df_MAR24['TIME'] = pd.to_datetime(df_MAR24['TIME'])
            df_SEP24['TIME'] = pd.to_datetime(df_SEP24['TIME'])
            df_MAR25['TIME'] = pd.to_datetime(df_MAR25['TIME'])
            df_SEP25['TIME'] = pd.to_datetime(df_SEP25['TIME'])

            # Set TIME as index for SEP24, MAR25, SEP25 (as they were resampled)
            # But only if TIME column exists
            if 'TIME' in df_SEP24.columns:
                df_SEP24.set_index('TIME', inplace=True)
            if 'TIME' in df_MAR25.columns:
                df_MAR25.set_index('TIME', inplace=True)
            if 'TIME' in df_SEP25.columns:
                df_SEP25.set_index('TIME', inplace=True)

            st.success(f"**Data reloaded and ready for visualization!**")

        except Exception as e:
            st.error(f"**Error during data reload process:** {e}")
            # Attempt to remove the temporary DB if it failed
            if os.path.exists(TEMP_DB_NAME):
                try:
                    os.remove(TEMP_DB_NAME)
                    st.warning(f"Failed temporary database `{TEMP_DB_NAME}` removed.")
                except:
                    st.error(f"Could not remove failed temporary database `{TEMP_DB_NAME}`.")
            st.stop()

    else: # Use existing database
        if db_exists:
            try:
                st.info(f"**Loading data from existing database `{DB_NAME}`...**")
                conn = sqlite3.connect(DB_NAME)
                df_SEP23 = pd.read_sql_query("SELECT * FROM df_SEP23", conn)
                df_MAR24 = pd.read_sql_query("SELECT * FROM df_MAR24", conn)
                df_SEP24 = pd.read_sql_query("SELECT * FROM df_SEP24", conn)
                df_MAR25 = pd.read_sql_query("SELECT * FROM df_MAR25", conn)
                df_SEP25 = pd.read_sql_query("SELECT * FROM df_SEP25", conn)
                conn.close()

                # Convert TIME columns back to datetime after reading from DB
                df_SEP23['TIME'] = pd.to_datetime(df_SEP23['TIME'])
                df_MAR24['TIME'] = pd.to_datetime(df_MAR24['TIME'])
                df_SEP24['TIME'] = pd.to_datetime(df_SEP24['TIME'])
                df_MAR25['TIME'] = pd.to_datetime(df_MAR25['TIME'])
                df_SEP25['TIME'] = pd.to_datetime(df_SEP25['TIME'])

                # Set TIME as index for SEP24, MAR25, SEP25 (as they were resampled)
                # But only if TIME column exists and is not already the index
                if 'TIME' in df_SEP24.columns and df_SEP24.index.name != 'TIME':
                    df_SEP24.set_index('TIME', inplace=True)
                if 'TIME' in df_MAR25.columns and df_MAR25.index.name != 'TIME':
                    df_MAR25.set_index('TIME', inplace=True)
                if 'TIME' in df_SEP25.columns and df_SEP25.index.name != 'TIME':
                    df_SEP25.set_index('TIME', inplace=True)

                # Check if MILLFILLING column exists in database, if not calculate it
                needs_update = False
                if 'MILLFILLING' not in df_SEP24.columns:
                    with st.spinner("Calculating Mill Filling for SEP24 (first time)..."):
                        # Reset index temporarily for calculation
                        df_SEP24_temp = df_SEP24.reset_index() if df_SEP24.index.name == 'TIME' else df_SEP24.copy()
                        df_SEP24_temp['MILLFILLING'] = calculate_mill_filling(df_SEP24_temp)
                        # Set index back
                        if df_SEP24.index.name == 'TIME':
                            df_SEP24_temp.set_index('TIME', inplace=True)
                        df_SEP24 = df_SEP24_temp
                    needs_update = True
                
                if 'MILLFILLING' not in df_MAR25.columns:
                    with st.spinner("Calculating Mill Filling for MAR25 (first time)..."):
                        # Reset index temporarily for calculation
                        df_MAR25_temp = df_MAR25.reset_index() if df_MAR25.index.name == 'TIME' else df_MAR25.copy()
                        df_MAR25_temp['MILLFILLING'] = calculate_mill_filling(df_MAR25_temp)
                        # Set index back
                        if df_MAR25.index.name == 'TIME':
                            df_MAR25_temp.set_index('TIME', inplace=True)
                        df_MAR25 = df_MAR25_temp
                    needs_update = True
                
                if 'MILLFILLING' not in df_SEP25.columns:
                    with st.spinner("Calculating Mill Filling for SEP25 (first time)..."):
                        # Reset index temporarily for calculation
                        df_SEP25_temp = df_SEP25.reset_index() if df_SEP25.index.name == 'TIME' else df_SEP25.copy()
                        df_SEP25_temp['MILLFILLING'] = calculate_mill_filling(df_SEP25_temp)
                        # Set index back
                        if df_SEP25.index.name == 'TIME':
                            df_SEP25_temp.set_index('TIME', inplace=True)
                        df_SEP25 = df_SEP25_temp
                    needs_update = True
                
                # Update database with MILLFILLING results if needed
                if needs_update:
                    st.info("Updating database with mill filling calculations...")
                    conn = sqlite3.connect(DB_NAME)
                    
                    # Reset index to store TIME as column for database
                    df_SEP24_db = df_SEP24.reset_index() if df_SEP24.index.name == 'TIME' else df_SEP24.copy()
                    df_MAR25_db = df_MAR25.reset_index() if df_MAR25.index.name == 'TIME' else df_MAR25.copy()
                    df_SEP25_db = df_SEP25.reset_index() if df_SEP25.index.name == 'TIME' else df_SEP25.copy()
                    
                    df_SEP24_db.to_sql('df_SEP24', conn, if_exists='replace', index=False)
                    df_MAR25_db.to_sql('df_MAR25', conn, if_exists='replace', index=False)
                    df_SEP25_db.to_sql('df_SEP25', conn, if_exists='replace', index=False)
                    conn.close()
                    
                    st.success("Database updated with mill filling calculations!")

            except Exception as e:
                st.error(f"**Error loading data from existing database:** {e}")
                st.stop()
        else:
            st.error(f"**Error: Database `{DB_NAME}` not found and reload option was not selected.**")
            st.stop()



    # --- Plotting Functions (using loaded dataframes) ---
    # --- Define aggregation functions ---
    def get_aggregated_data(df, agg_period, col_x, col_y):
        """Helper function to get aggregated data for plotting."""
        if agg_period == "per Hour":
            resampled_df = df.resample('H').mean()
        elif agg_period == "per Shift": # 12 hours
            resampled_df = df.resample('12H').mean()
        elif agg_period == "per Day": # 24 hours
            resampled_df = df.resample('D').mean()
        elif agg_period == "per Week": # Weekly (Monday)
            resampled_df = df.resample('W-MON').mean()
        elif agg_period == "per Month": # Monthly
            resampled_df = df.resample('ME').mean()
        else:
            return df[col_x], df[col_y] # Return original if no match

        # Only keep rows where both x and y are not NaN
        resampled_df = resampled_df.dropna(subset=[col_x, col_y])
        return resampled_df[col_x], resampled_df[col_y]

    def plot_pebble_rate_cumfeed():
        # Initialize session state for this plot's aggregation options if not exists
        if 'agg_pebble_cumfeed' not in st.session_state:
            st.session_state.agg_pebble_cumfeed = []
        if 'fig_pebble_cumfeed' not in st.session_state:
            st.session_state.fig_pebble_cumfeed = None
        # Define aggregation options
        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]
        # Controls for this plot - MOVED TO THE TAB
        with st.container():
            col1, col2 = st.columns([1, 1], vertical_alignment = "bottom") # Adjust column ratio as needed
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_pebble_cumfeed, key="agg_multiselect_pebble_cumfeed")
            with col2:
                update_chart = st.button("Update Chart", key="update_pebble_cumfeed")
        # Update session state if button is clicked
        if update_chart:
            st.session_state.agg_pebble_cumfeed = selected_agg
        # Create the base figure if it doesn't exist or needs updating
        if st.session_state.fig_pebble_cumfeed is None or update_chart:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_SEP23['CUMFEED'], y=df_SEP23['PEBBLE'],
                                    name='Transient Pebble Rate - SEP23', mode='lines', opacity=0.3,
                                    line=dict(color='black')))
            fig.add_trace(go.Scatter(x=df_MAR24['CUMFEED'], y=df_MAR24['PEBBLE'],
                                    name='Transient Pebble Rate - MAR24', mode='lines', opacity=0.4,
                                    line=dict(color='red')))
            fig.add_trace(go.Scatter(x=df_SEP24['CUMFEED'], y=df_SEP24['PEBBLE'],
                                    name='Transient Pebble Rate - SEP24', mode='lines', opacity=0.5,
                                    line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=df_MAR25['CUMFEED'], y=df_MAR25['PEBBLE'],
                                    name='Transient Pebble Rate - MAR25', mode='lines', opacity=0.2,
                                    line=dict(color='green')))
            fig.add_trace(go.Scatter(x=df_SEP25['CUMFEED'], y=df_SEP25['PEBBLE'],
                                    name='Transient Pebble Rate - SEP25', mode='lines', opacity=0.8,
                                    line=dict(color='purple')))
            
            # --- Linear Fit for df_SEP25 ---
            # Prepare data for fitting (remove NaNs)
            fit_data = df_SEP25[['CUMFEED', 'PEBBLE']].dropna()
            if not fit_data.empty:
                from numpy import polyfit
                # Calculate linear fit coefficients (slope and intercept)
                coeffs = polyfit(fit_data['CUMFEED'], fit_data['PEBBLE'], 1)
                slope, intercept = coeffs
                # Define x values for the fit line (extended to 2000000)
                x_fit = [fit_data['CUMFEED'].min(), 2000000] # Extend to xaxis = 2000000
                y_fit = [slope * x + intercept for x in x_fit]
                
                # Add the fit line trace with the same color as df_SEP25 ('purple')
                # Use a different line style (e.g., dash) to distinguish it
                fig.add_trace(go.Scatter(x=x_fit, y=y_fit,
                                        name='Pebble Rate - SEP25 (Linear Fit)', 
                                        mode='lines',
                                        line=dict(color='purple', dash='dash', width=2),
                                        opacity=0.8))
            # --- End of Linear Fit ---
            
            # Add aggregated traces based on session state
            for agg_period in st.session_state.agg_pebble_cumfeed:
                # Aggregate for each dataframe used in the plot
                for df, name, color in [(df_SEP25, 'SEP25', 'purple'), (df_MAR25, 'MAR25', 'green'), (df_SEP24, 'SEP24', 'blue')]:
                    if df is not None and not df.empty:
                        x_agg, y_agg = get_aggregated_data(df, agg_period, 'CUMFEED', 'PEBBLE')
                        fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                                name=f'Pebble Rate - {name} ({agg_period})', mode='lines',
                                                line=dict(color=color, dash='dot', width=1.5), opacity=0.7))
            
            # Add horizontal line at y=650
            fig.add_hline(y=650, line=dict(color='red', width=3), name='Threshold Line 650')
            fig.add_hline(y=550, line=dict(color='orange', width=3), name='Threshold Line 550')
            
            fig.update_yaxes(title_text="Pebble Rate (t/h)", showgrid=True)
            fig.update_xaxes(title_text="Cumulative MT Milled", showgrid=True)
            fig.update_yaxes(range=[100, 700])
            fig.update_xaxes(range=[0, 4000000])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.75))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=100, dtick=20))
            fig.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=100000))
            fig.update_layout(height=640)
            st.session_state.fig_pebble_cumfeed = fig

        return st.session_state.fig_pebble_cumfeed

    def plot_milling_rate_cumfeed():
        if 'agg_milling_cumfeed' not in st.session_state:
            st.session_state.agg_milling_cumfeed = []
        if 'fig_milling_cumfeed' not in st.session_state:
            st.session_state.fig_milling_cumfeed = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_milling_cumfeed, key="agg_multiselect_milling_cumfeed")
            with col2:
                update_chart = st.button("Update Chart", key="update_milling_cumfeed")

        if update_chart:
            st.session_state.agg_milling_cumfeed = selected_agg

        if st.session_state.fig_milling_cumfeed is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_SEP23['CUMFEED'], y=df_SEP23['FEED'],
                                    name='Milling Rate - SEP23', mode='lines', opacity=0.3,
                                    line=dict(color='black')))
            fig.add_trace(go.Scatter(x=df_MAR24['CUMFEED'], y=df_MAR24['FEED'],
                                    name='Milling Rate - MAR24', mode='lines', opacity=0.4,
                                    line=dict(color='red')))
            fig.add_trace(go.Scatter(x=df_SEP24['CUMFEED'], y=df_SEP24['FEED'],
                                    name='Milling Rate - SEP24', mode='lines', opacity=0.2,
                                    line=dict(color='blue')))
            fig.add_trace(go.Scatter(x=df_MAR25['CUMFEED'], y=df_MAR25['FEED'],
                                    name='Milling Rate - MAR25', mode='lines', opacity=0.3,
                                    line=dict(color='green')))
            fig.add_trace(go.Scatter(x=df_SEP25['CUMFEED'], y=df_SEP25['FEED'],
                                    name='Milling Rate - SEP25', mode='lines', opacity=0.7,
                                    line=dict(color='purple')))

            for agg_period in st.session_state.agg_milling_cumfeed:
                for df, name, color in [(df_SEP25, 'SEP25', 'purple'), (df_MAR25, 'MAR25', 'green'), (df_SEP24, 'SEP24', 'blue')]:
                    if df is not None and not df.empty:
                        x_agg, y_agg = get_aggregated_data(df, agg_period, 'CUMFEED', 'FEED')
                        fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                                name=f'Milling Rate - {name} ({agg_period})', mode='lines',
                                                line=dict(color=color, dash='dot', width=1.5), opacity=0.7))

            fig.update_yaxes(title_text="Milling Rate (t/h)", showgrid=True)
            fig.update_xaxes(title_text="Cumulative MT Milled", showgrid=True)
            fig.update_yaxes(range=[600, 1200])
            fig.update_xaxes(range=[0, 4000000])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.75))
            fig.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=100000))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=600, dtick=20))
            fig.update_layout(height=640)

            st.session_state.fig_milling_cumfeed = fig

        return st.session_state.fig_milling_cumfeed

    def plot_pebble_rate_time():
        if 'agg_pebble_time' not in st.session_state:
            st.session_state.agg_pebble_time = []
        if 'fig_pebble_time' not in st.session_state:
            st.session_state.fig_pebble_time = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_pebble_time, key="agg_multiselect_pebble_time")
            with col2:
                update_chart = st.button("Update Chart", key="update_pebble_time")

        if update_chart:
            st.session_state.agg_pebble_time = selected_agg

        if st.session_state.fig_pebble_time is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_SEP25.index, y=df_SEP25['PEBBLE'],
                                    name='Pebble Rate - SEP25', mode='lines', opacity=0.5,
                                    line=dict(color='green')))

            for agg_period in st.session_state.agg_pebble_time:
                x_agg, y_agg = get_aggregated_data(df_SEP25, agg_period, 'TIME', 'PEBBLE')
                fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                        name=f'Pebble Rate - SEP25 ({agg_period})', mode='lines',
                                        line=dict(color='green', dash='dot', width=1.5), opacity=0.7))

            fig.update_yaxes(title_text="Pebble Rate - tph", showgrid=True)
            fig.update_xaxes(title_text="Time", showgrid=True)
            fig.update_yaxes(range=[100, 700])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=100, dtick=20))
            fig.update_layout(height=640)

            st.session_state.fig_pebble_time = fig

        return st.session_state.fig_pebble_time

    def plot_cumulative_tons_time():
        if 'agg_cum_tons_time' not in st.session_state:
            st.session_state.agg_cum_tons_time = []
        if 'fig_cum_tons_time' not in st.session_state:
            st.session_state.fig_cum_tons_time = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_cum_tons_time, key="agg_multiselect_cum_tons_time")
            with col2:
                update_chart = st.button("Update Chart", key="update_cum_tons_time")

        if update_chart:
            st.session_state.agg_cum_tons_time = selected_agg

        if st.session_state.fig_cum_tons_time is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_SEP25.index, y=df_SEP25['CUMFEED'],
                                    name='Cumulative Tons - SEP25', mode='lines', opacity=0.5,
                                    line=dict(color='orange')))

            for agg_period in st.session_state.agg_cum_tons_time:
                x_agg, y_agg = get_aggregated_data(df_SEP25, agg_period, 'TIME', 'CUMFEED')
                fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                        name=f'Cumulative Tons - SEP25 ({agg_period})', mode='lines',
                                        line=dict(color='orange', dash='dot', width=1.5), opacity=0.7))

            fig.update_yaxes(title_text="Cumulative Tons - t", showgrid=True)
            fig.update_xaxes(title_text="Time", showgrid=True)
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(height=640)

            st.session_state.fig_cum_tons_time = fig

        return st.session_state.fig_cum_tons_time

    def plot_fresh_feed_time():
        if 'agg_fresh_feed_time' not in st.session_state:
            st.session_state.agg_fresh_feed_time = []
        if 'fig_fresh_feed_time' not in st.session_state:
            st.session_state.fig_fresh_feed_time = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_fresh_feed_time, key="agg_multiselect_fresh_feed_time")
            with col2:
                update_chart = st.button("Update Chart", key="update_fresh_feed_time")

        if update_chart:
            st.session_state.agg_fresh_feed_time = selected_agg

        if st.session_state.fig_fresh_feed_time is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_SEP25.index, y=df_SEP25['FEED'],
                                    name='Fresh Feed - SEP25', mode='lines', opacity=0.5,
                                    line=dict(color='orange')))

            for agg_period in st.session_state.agg_fresh_feed_time:
                x_agg, y_agg = get_aggregated_data(df_SEP25, agg_period, 'TIME', 'FEED')
                fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                        name=f'Fresh Feed - SEP25 ({agg_period})', mode='lines',
                                        line=dict(color='orange', dash='dot', width=1.5), opacity=0.7))

            fig.update_yaxes(title_text="Fresh Feed - tph", showgrid=True)
            fig.update_xaxes(title_text="Time", showgrid=True)
            fig.update_yaxes(range=[600, 1200])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=100, dtick=20))
            fig.update_layout(height=640)

            st.session_state.fig_fresh_feed_time = fig

        return st.session_state.fig_fresh_feed_time

    def plot_mill_availability_time():
        if 'agg_mill_availability_time' not in st.session_state:
            st.session_state.agg_mill_availability_time = []
        if 'fig_mill_availability_time' not in st.session_state:
            st.session_state.fig_mill_availability_time = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_mill_availability_time, key="agg_multiselect_mill_availability_time")
            with col2:
                update_chart = st.button("Update Chart", key="update_mill_availability_time")

        if update_chart:
            st.session_state.agg_mill_availability_time = selected_agg

        if st.session_state.fig_mill_availability_time is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_SEP25.index, y=df_SEP25['MILL_AVAILABILITY'],
                                    name='MILL_Runtime - SEP25', mode='lines',
                                    fill='tozeroy',
                                    fillcolor='rgba(0, 100, 80, 0.2)',
                                    line=dict(color='rgb(0, 100, 80)')))

            for agg_period in st.session_state.agg_mill_availability_time:
                x_agg, y_agg = get_aggregated_data(df_SEP25, agg_period, 'TIME', 'MILL_AVAILABILITY')
                fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                        name=f'MILL_AVAILABILITY - SEP25 ({agg_period})', mode='lines',
                                        line=dict(color='rgb(0, 100, 80)', dash='dot', width=1.5), opacity=0.7, fill='tozeroy', fillcolor='rgba(0, 100, 80, 0.1)'))

            fig.update_yaxes(title_text="Mill Runtime - %", showgrid=True)
            fig.update_xaxes(title_text="Time", showgrid=True)
            fig.update_yaxes(range=[75, 100])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=70, dtick=5))
            fig.update_layout(height=640)

            st.session_state.fig_mill_availability_time = fig

        return st.session_state.fig_mill_availability_time

    def plot_mill_load_time():
        if 'agg_mill_load_time' not in st.session_state:
            st.session_state.agg_mill_load_time = []
        if 'fig_mill_load_time' not in st.session_state:
            st.session_state.fig_mill_load_time = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_mill_load_time, key="agg_multiselect_mill_load_time")
            with col2:
                update_chart = st.button("Update Chart", key="update_mill_load_time")

        if update_chart:
            st.session_state.agg_mill_load_time = selected_agg

        if st.session_state.fig_mill_load_time is None or update_chart:
            fig = go.Figure()

            # Calculate weekly average for original trace as in the original code
            df_SEP25_weekly = df_SEP25.resample('W-MON').mean()
            fig.add_trace(go.Scatter(x=df_SEP25_weekly.index, y=df_SEP25_weekly['LOAD'],
                                    name='MILL LOAD - SEP25 (Weekly Avg)', mode='lines',
                                    fill='tozeroy',
                                    fillcolor='rgba(0, 100, 80, 0.2)',
                                    line=dict(color='rgb(0, 100, 80)')))

            for agg_period in st.session_state.agg_mill_load_time:
                x_agg, y_agg = get_aggregated_data(df_SEP25, agg_period, 'TIME', 'LOAD')
                fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                        name=f'MILL LOAD - SEP25 ({agg_period})', mode='lines',
                                        line=dict(color='rgb(0, 100, 80)', dash='dot', width=1.5), opacity=0.7, fill='tozeroy', fillcolor='rgba(0, 100, 80, 0.1)'))

            fig.update_yaxes(title_text="MILL LOAD - ton", showgrid=True)
            fig.update_xaxes(title_text="Time", showgrid=True)
            fig.update_yaxes(range=[700, 1400])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=400, dtick=100))
            fig.update_layout(height=640)

            st.session_state.fig_mill_load_time = fig

        return st.session_state.fig_mill_load_time

    def plot_mill_load_cumtons():
        if 'agg_mill_load_cumtons' not in st.session_state:
            st.session_state.agg_mill_load_cumtons = []
        if 'fig_mill_load_cumtons' not in st.session_state:
            st.session_state.fig_mill_load_cumtons = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_mill_load_cumtons, key="agg_multiselect_mill_load_cumtons")
            with col2:
                update_chart = st.button("Update Chart", key="update_mill_load_cumtons")

        if update_chart:
            st.session_state.agg_mill_load_cumtons = selected_agg

        if st.session_state.fig_mill_load_cumtons is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_SEP25['CUMFEED'], y=df_SEP25['LOAD'],
                                    name='Mill Load - SEP25', mode='lines', opacity=0.8,
                                    line=dict(color='purple')))
            fig.add_trace(go.Scatter(x=df_MAR25['CUMFEED'], y=df_MAR25['LOAD'],
                                    name='Mill Load - MAR25', mode='lines', opacity=0.5,
                                    line=dict(color='orange')))
            fig.add_trace(go.Scatter(x=df_SEP24['CUMFEED'], y=df_SEP24['LOAD'],
                                    name='Mill Load - SEP24', mode='lines', opacity=0.3,
                                    line=dict(color='blue')))

            for agg_period in st.session_state.agg_mill_load_cumtons:
                for df, name, color in [(df_SEP25, 'SEP25', 'purple'), (df_MAR25, 'MAR25', 'orange'), (df_SEP24, 'SEP24', 'blue')]:
                    if df is not None and not df.empty:
                        x_agg, y_agg = get_aggregated_data(df, agg_period, 'CUMFEED', 'LOAD')
                        fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                                name=f'Mill Load - {name} ({agg_period})', mode='lines',
                                                line=dict(color=color, dash='dot', width=1.5), opacity=0.7))

            fig.update_yaxes(title_text="MILL LOAD - ton", showgrid=True)
            fig.update_xaxes(title_text="Cumulative Tons Milled", showgrid=True)
            fig.update_yaxes(range=[700, 1400])
            fig.update_xaxes(range=[0, 4000000])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.75))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=100, dtick=20))
            fig.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=100000))
            fig.update_layout(height=640)

            st.session_state.fig_mill_load_cumtons = fig

        return st.session_state.fig_mill_load_cumtons

    def plot_mill_power_load_cumtons():
        if 'agg_mill_power_load_cumtons' not in st.session_state:
            st.session_state.agg_mill_power_load_cumtons = []
        if 'fig_mill_power_load_cumtons' not in st.session_state:
            st.session_state.fig_mill_power_load_cumtons = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_mill_power_load_cumtons, key="agg_multiselect_mill_power_load_cumtons")
            with col2:
                update_chart = st.button("Update Chart", key="update_mill_power_load_cumtons")

        if update_chart:
            st.session_state.agg_mill_power_load_cumtons = selected_agg

        if st.session_state.fig_mill_power_load_cumtons is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_SEP25['CUMFEED'], y=df_SEP25['LOAD'],
                                    name='Mill Load - SEP25', mode='lines', opacity=0.8,
                                    line=dict(color='purple')))
            fig.add_trace(go.Scatter(x=df_MAR25['CUMFEED'], y=df_MAR25['LOAD'],
                                    name='Mill Load - MAR25', mode='lines', opacity=0.5,
                                    line=dict(color='orange')))
            fig.add_trace(go.Scatter(x=df_SEP24['CUMFEED'], y=df_SEP24['LOAD'],
                                    name='Mill Load - SEP24', mode='lines', opacity=0.3,
                                    line=dict(color='blue')))

            fig.add_trace(go.Scatter(x=df_SEP25['CUMFEED'], y=df_SEP25['POWER'],
                                    name='Mill POWER - SEP25', yaxis="y2", mode='lines', opacity=0.8,
                                    line=dict(color='purple', width=2, dash='dashdot')))
            fig.add_trace(go.Scatter(x=df_MAR25['CUMFEED'], y=df_MAR25['POWER'],
                                    name='Mill POWER - MAR25', yaxis="y2", mode='lines', opacity=0.5,
                                    line=dict(color='orange', width=2, dash='dashdot')))
            fig.add_trace(go.Scatter(x=df_SEP24['CUMFEED'], y=df_SEP24['POWER'],
                                    name='Mill POWER - SEP24', yaxis="y2", mode='lines', opacity=0.3,
                                    line=dict(color='blue', width=2, dash='dashdot')))

            for agg_period in st.session_state.agg_mill_power_load_cumtons:
                for df, name, color_load, color_power in [(df_SEP25, 'SEP25', 'purple', 'purple'), (df_MAR25, 'MAR25', 'orange', 'orange'), (df_SEP24, 'SEP24', 'blue', 'blue')]:
                    if df is not None and not df.empty:
                        # Aggregate Load
                        x_agg_load, y_agg_load = get_aggregated_data(df, agg_period, 'CUMFEED', 'LOAD')
                        fig.add_trace(go.Scatter(x=x_agg_load, y=y_agg_load,
                                                name=f'Mill Load - {name} ({agg_period})', mode='lines',
                                                line=dict(color=color_load, dash='dot', width=1.5), opacity=0.7))

                        # Aggregate Power
                        x_agg_power, y_agg_power = get_aggregated_data(df, agg_period, 'CUMFEED', 'POWER')
                        fig.add_trace(go.Scatter(x=x_agg_power, y=y_agg_power,
                                                name=f'Mill POWER - {name} ({agg_period})', yaxis="y2", mode='lines',
                                                line=dict(color=color_power, dash='dot', width=1.5), opacity=0.7))

            fig.update_layout(
                yaxis=dict(title="MILL LOAD - ton", range=[700, 1400]),
                yaxis2=dict(title="MILL POWER - kW", range=[10000, 30000], overlaying="y", side="right")
            )
            fig.update_xaxes(title_text="Cumulative Tons Milled", showgrid=True)
            fig.update_xaxes(range=[0, 3000000])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.75))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=100, dtick=20))
            fig.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=100000))
            fig.update_layout(height=640)

            st.session_state.fig_mill_power_load_cumtons = fig

        return st.session_state.fig_mill_power_load_cumtons

    def plot_mill_load_vs_feed():
        if 'agg_mill_load_vs_feed' not in st.session_state:
            st.session_state.agg_mill_load_vs_feed = []
        if 'fig_mill_load_vs_feed' not in st.session_state:
            st.session_state.fig_mill_load_vs_feed = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_mill_load_vs_feed, key="agg_multiselect_mill_load_vs_feed")
            with col2:
                update_chart = st.button("Update Chart", key="update_mill_load_vs_feed")

        if update_chart:
            st.session_state.agg_mill_load_vs_feed = selected_agg

        if st.session_state.fig_mill_load_vs_feed is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_MAR25['LOAD'], y=df_MAR25['FEED'],
                                    name='Fresh Feed - MAR25', mode='markers', opacity=0.2,
                                    marker=dict(color='orange')))
            fig.add_trace(go.Scatter(x=df_SEP25['LOAD'], y=df_SEP25['FEED'],
                                    name='Fresh Feed - SEP25', mode='markers', opacity=0.8,
                                    marker=dict(color='purple')))
            fig.add_trace(go.Scatter(x=df_SEP24['LOAD'], y=df_SEP24['FEED'],
                                    name='Fresh Feed - SEP24', mode='markers', opacity=0.2,
                                    marker=dict(color='blue')))

            for agg_period in st.session_state.agg_mill_load_vs_feed:
                for df, name, color in [(df_SEP25, 'SEP25', 'purple'), (df_MAR25, 'MAR25', 'orange'), (df_SEP24, 'SEP24', 'blue')]:
                    if df is not None and not df.empty:
                        x_agg, y_agg = get_aggregated_data(df, agg_period, 'LOAD', 'FEED')
                        fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                                name=f'Fresh Feed - {name} ({agg_period})', mode='markers',
                                                marker=dict(color=color, size=4), opacity=0.7))

            fig.update_yaxes(title_text="Fresh Feed - tph", showgrid=True)
            fig.update_xaxes(title_text="Mill Load - tons", showgrid=True)
            fig.update_yaxes(range=[400, 1200])
            fig.update_xaxes(range=[500, 1400])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=100, dtick=20))
            fig.update_layout(height=640)

            st.session_state.fig_mill_load_vs_feed = fig

        return st.session_state.fig_mill_load_vs_feed

    def plot_mill_power_vs_load():
        if 'agg_mill_power_vs_load' not in st.session_state:
            st.session_state.agg_mill_power_vs_load = []
        if 'fig_mill_power_vs_load' not in st.session_state:
            st.session_state.fig_mill_power_vs_load = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_mill_power_vs_load, key="agg_multiselect_mill_power_vs_load")
            with col2:
                update_chart = st.button("Update Chart", key="update_mill_power_vs_load")

        if update_chart:
            st.session_state.agg_mill_power_vs_load = selected_agg

        if st.session_state.fig_mill_power_vs_load is None or update_chart:
            fig = go.Figure()

            fig.add_trace(go.Scatter(x=df_MAR25['LOAD'], y=df_MAR25['POWER'],
                                    name='Mill Power - MAR25', mode='markers', opacity=0.2,
                                    marker=dict(color='orange')))
            fig.add_trace(go.Scatter(x=df_SEP25['LOAD'], y=df_SEP25['POWER'],
                                    name='Mill Power - SEP25', mode='markers', opacity=0.8,
                                    marker=dict(color='purple')))
            fig.add_trace(go.Scatter(x=df_SEP24['LOAD'], y=df_SEP24['POWER'],
                                    name='Mill Power - SEP24', mode='markers', opacity=0.2,
                                    marker=dict(color='blue')))

            for agg_period in st.session_state.agg_mill_power_vs_load:
                for df, name, color in [(df_SEP25, 'SEP25', 'purple'), (df_MAR25, 'MAR25', 'orange'), (df_SEP24, 'SEP24', 'blue')]:
                    if df is not None and not df.empty:
                        x_agg, y_agg = get_aggregated_data(df, agg_period, 'LOAD', 'POWER')
                        fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                                name=f'Mill Power - {name} ({agg_period})', mode='markers',
                                                marker=dict(color=color, size=4), opacity=0.7))

            fig.update_yaxes(title_text="Mill Power - kW", showgrid=True)
            fig.update_xaxes(title_text="Mill Load - tons", showgrid=True)
            fig.update_yaxes(range=[10000, 20000])
            fig.update_xaxes(range=[500, 1400])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=10000, dtick=1000))
            fig.update_layout(height=640)

            st.session_state.fig_mill_power_vs_load = fig

        return st.session_state.fig_mill_power_vs_load


    def plot_mill_filling_cumfeed():
        if 'agg_mill_filling_cumfeed' not in st.session_state:
            st.session_state.agg_mill_filling_cumfeed = []
        if 'fig_mill_filling_cumfeed' not in st.session_state:
            st.session_state.fig_mill_filling_cumfeed = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_mill_filling_cumfeed, key="agg_multiselect_mill_filling_cumfeed")
            with col2:
                update_chart = st.button("Update Chart", key="update_mill_filling_cumfeed")

        if update_chart:
            st.session_state.agg_mill_filling_cumfeed = selected_agg

        if st.session_state.fig_mill_filling_cumfeed is None or update_chart:
            fig = go.Figure()

            # Only plot dataframes that have MILLFILLING column
            if 'MILLFILLING' in df_SEP24.columns:
                fig.add_trace(go.Scatter(x=df_SEP24['CUMFEED'], y=df_SEP24['MILLFILLING'],
                                        name='Mill Filling - SEP24', mode='lines', opacity=0.5,
                                        line=dict(color='blue')))
            
            if 'MILLFILLING' in df_MAR25.columns:
                fig.add_trace(go.Scatter(x=df_MAR25['CUMFEED'], y=df_MAR25['MILLFILLING'],
                                        name='Mill Filling - MAR25', mode='lines', opacity=0.5,
                                        line=dict(color='green')))
            
            if 'MILLFILLING' in df_SEP25.columns:
                fig.add_trace(go.Scatter(x=df_SEP25['CUMFEED'], y=df_SEP25['MILLFILLING'],
                                        name='Mill Filling - SEP25', mode='lines', opacity=0.8,
                                        line=dict(color='purple')))

            for agg_period in st.session_state.agg_mill_filling_cumfeed:
                for df, name, color in [(df_SEP25, 'SEP25', 'purple'), (df_MAR25, 'MAR25', 'green'), (df_SEP24, 'SEP24', 'blue')]:
                    if df is not None and not df.empty and 'MILLFILLING' in df.columns:
                        x_agg, y_agg = get_aggregated_data(df, agg_period, 'CUMFEED', 'MILLFILLING')
                        fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                                name=f'Mill Filling - {name} ({agg_period})', mode='lines',
                                                line=dict(color=color, dash='dot', width=1.5), opacity=0.7))

            fig.update_yaxes(title_text="Mill Filling - fraction", showgrid=True)
            fig.update_xaxes(title_text="Cumulative MT Milled", showgrid=True)
            fig.update_yaxes(range=[0.1, 0.55])  # Typical mill filling range
            fig.update_xaxes(range=[0, 4000000])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.75))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=0.1, dtick=0.05))
            fig.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=100000))
            fig.update_layout(height=640)

            st.session_state.fig_mill_filling_cumfeed = fig

        return st.session_state.fig_mill_filling_cumfeed


    # Add these two new plotting functions before the Streamlit App Layout section
    def plot_silica_cumfeed():
        if 'agg_silica_cumfeed' not in st.session_state:
            st.session_state.agg_silica_cumfeed = []
        if 'fig_silica_cumfeed' not in st.session_state:
            st.session_state.fig_silica_cumfeed = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_silica_cumfeed, key="agg_multiselect_silica_cumfeed")
            with col2:
                update_chart = st.button("Update Chart", key="update_silica_cumfeed")

        if update_chart:
            st.session_state.agg_silica_cumfeed = selected_agg

        if st.session_state.fig_silica_cumfeed is None or update_chart:
            fig = go.Figure()

            # Plot Silica vs Cumulative Feed for each dataset that has SILICA data
            if 'SILICA' in df_SEP23.columns:
                fig.add_trace(go.Scatter(x=df_SEP23['CUMFEED'], y=df_SEP23['SILICA'],
                                        name='Silica - SEP23', mode='lines', opacity=0.3,
                                        line=dict(color='black')))
            
            if 'SILICA' in df_MAR24.columns:
                fig.add_trace(go.Scatter(x=df_MAR24['CUMFEED'], y=df_MAR24['SILICA'],
                                        name='Silica - MAR24', mode='lines', opacity=0.4,
                                        line=dict(color='red')))
            
            if 'SILICA' in df_SEP24.columns:
                fig.add_trace(go.Scatter(x=df_SEP24['CUMFEED'], y=df_SEP24['SILICA'],
                                        name='Silica - SEP24', mode='lines', opacity=0.5,
                                        line=dict(color='blue')))
            
            if 'SILICA' in df_MAR25.columns:
                fig.add_trace(go.Scatter(x=df_MAR25['CUMFEED'], y=df_MAR25['SILICA'],
                                        name='Silica - MAR25', mode='lines', opacity=0.2,
                                        line=dict(color='green')))
                
            if 'SILICA' in df_SEP25.columns:
                fig.add_trace(go.Scatter(x=df_SEP25['CUMFEED'], y=df_SEP25['SILICA'],
                                        name='Silica - SEP25', mode='lines', opacity=1.0,
                                        line=dict(color='purple')))

            for agg_period in st.session_state.agg_silica_cumfeed:
                for df, name, color in [(df_SEP23, 'SEP23', 'black'), (df_MAR24, 'MAR24', 'red'), 
                                    (df_SEP24, 'SEP24', 'blue'), (df_MAR25, 'MAR25', 'green'),
                                    (df_SEP25, 'SEP25', 'purple')]:
                    if df is not None and not df.empty and 'SILICA' in df.columns:
                        x_agg, y_agg = get_aggregated_data(df, agg_period, 'CUMFEED', 'SILICA')
                        fig.add_trace(go.Scatter(x=x_agg, y=y_agg,
                                                name=f'Silica - {name} ({agg_period})', mode='lines',
                                                line=dict(color=color, dash='dot', width=1.5), opacity=0.7))

            fig.update_yaxes(title_text="Silica (%)", showgrid=True)
            fig.update_xaxes(title_text="Cumulative MT Milled", showgrid=True)
            fig.update_yaxes(range=[20, 50])  # Adjust range based on typical silica values
            fig.update_xaxes(range=[0, 4000000])
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.75))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=0, dtick=10))
            fig.update_layout(xaxis=dict(tickmode='linear', tick0=0.0, dtick=100000))
            fig.update_layout(height=640)

            st.session_state.fig_silica_cumfeed = fig

        return st.session_state.fig_silica_cumfeed

    def plot_silica_timeseries():
        if 'agg_silica_time' not in st.session_state:
            st.session_state.agg_silica_time = []
        if 'fig_silica_time' not in st.session_state:
            st.session_state.fig_silica_time = None

        agg_options = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_agg = st.multiselect("Select aggregation periods for this chart:", agg_options, default=st.session_state.agg_silica_time, key="agg_multiselect_silica_time")
            with col2:
                update_chart = st.button("Update Chart", key="update_silica_time")

        if update_chart:
            st.session_state.agg_silica_time = selected_agg

        if st.session_state.fig_silica_time is None or update_chart:
            fig = go.Figure()

            # Combine all silica data into one timeseries
            all_silica_data = []
            
            # SEP23 data
            if 'SILICA' in df_SEP23.columns and not df_SEP23.empty:
                sep23_data = df_SEP23[['TIME', 'SILICA']].copy()
                sep23_data['Dataset'] = 'SEP23'
                all_silica_data.append(sep23_data)
            
            # MAR24 data
            if 'SILICA' in df_MAR24.columns and not df_MAR24.empty:
                mar24_data = df_MAR24[['TIME', 'SILICA']].copy()
                mar24_data['Dataset'] = 'MAR24'
                all_silica_data.append(mar24_data)
            
            # SEP24 data
            if 'SILICA' in df_SEP24.columns and not df_SEP24.empty:
                sep24_data = df_SEP24.reset_index()[['TIME', 'SILICA']].copy()
                sep24_data['Dataset'] = 'SEP24'
                all_silica_data.append(sep24_data)
            
            # MAR25 data
            if 'SILICA' in df_MAR25.columns and not df_MAR25.empty:
                mar25_data = df_MAR25.reset_index()[['TIME', 'SILICA']].copy()
                mar25_data['Dataset'] = 'MAR25'
                all_silica_data.append(mar25_data)

            # SEP25 data
            if 'SILICA' in df_SEP25.columns and not df_SEP25.empty:
                sep25_data = df_SEP25.reset_index()[['TIME', 'SILICA']].copy()
                sep25_data['Dataset'] = 'SEP25'
                all_silica_data.append(sep25_data)

            # Combine all data
            if all_silica_data:
                combined_silica = pd.concat(all_silica_data, ignore_index=True)
                combined_silica = combined_silica.sort_values('TIME')
                
                # Plot the combined timeseries
                for dataset in combined_silica['Dataset'].unique():
                    dataset_data = combined_silica[combined_silica['Dataset'] == dataset]
                    color_map = {'SEP23': 'black', 'MAR24': 'red', 'SEP24': 'blue', 'MAR25': 'green', 'SEP25': 'purple'}
                    
                    fig.add_trace(go.Scatter(x=dataset_data['TIME'], y=dataset_data['SILICA'],
                                            name=f'Silica - {dataset}', mode='lines',
                                            line=dict(color=color_map.get(dataset, 'gray')),
                                            opacity=0.7))

                # Add aggregated traces if selected
                for agg_period in st.session_state.agg_silica_time:
                    # Resample the combined data
                    combined_silica_indexed = combined_silica.set_index('TIME')
                    
                    if agg_period == "per Hour":
                        resampled_df = combined_silica_indexed.resample('H').mean()
                    elif agg_period == "per Shift":
                        resampled_df = combined_silica_indexed.resample('12H').mean()
                    elif agg_period == "per Day":
                        resampled_df = combined_silica_indexed.resample('D').mean()
                    elif agg_period == "per Week":
                        resampled_df = combined_silica_indexed.resample('W-MON').mean()
                    elif agg_period == "per Month":
                        resampled_df = combined_silica_indexed.resample('ME').mean()
                    else:
                        resampled_df = combined_silica_indexed
                    
                    fig.add_trace(go.Scatter(x=resampled_df.index, y=resampled_df['SILICA'],
                                            name=f'Silica - All Data ({agg_period})', mode='lines',
                                            line=dict(color='purple', dash='dot', width=2),
                                            opacity=0.8))

            fig.update_yaxes(title_text="Silica (%)", showgrid=True)
            fig.update_xaxes(title_text="Time", showgrid=True)
            fig.update_yaxes(range=[20, 50])  # Adjust range based on typical silica values
            fig.update_layout(
                margin=dict(l=1, r=1, t=50, b=50),
                template="simple_white",
                showlegend=True,
                font=dict(size=12, color="Black")
            )
            fig.update_layout(legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.03))
            fig.update_layout(yaxis=dict(tickmode='linear', tick0=0, dtick=10))
            fig.update_layout(height=640)

            st.session_state.fig_silica_time = fig

        return st.session_state.fig_silica_time

    # Then update the plot_options in the Streamlit App Layout section:

    # --- Streamlit App Layout ---
    st.markdown("###")
    st.subheader(":material/Cadence: Performance Plots", divider = 'gray')

    # Create a selectbox for plot selection
    plot_options = [
        "Pebble Rate vs CumFeed",
        "Milling Rate vs CumFeed", 
        "Pebble Rate vs Time",
        "Cum Tons vs Time",
        "Fresh Feed vs Time",
        "Mill Runtime vs Time",
        "Mill Load vs Time",
        "Mill Load vs Cum Tons",
        "Power & Load vs Cum Tons",
        "Load vs Feed Rate",
        "Power vs Load",
        "Mill Filling vs CumFeed",
        "Silica vs CumFeed",  # Added new plot
        "Silica Timeseries"   # Added new plot
    ]
    selected_plot = st.selectbox("Select a plot to display:", plot_options)

    # Display the selected plot
    if selected_plot == "Pebble Rate vs CumFeed":
        st.subheader("Pebble Rate vs Cumulative Feed")
        fig1 = plot_pebble_rate_cumfeed()
        st.plotly_chart(fig1, use_container_width=True)
    elif selected_plot == "Milling Rate vs CumFeed":
        st.subheader("Milling Rate vs Cumulative Feed")
        fig2 = plot_milling_rate_cumfeed()
        st.plotly_chart(fig2, use_container_width=True)
    elif selected_plot == "Pebble Rate vs Time":
        st.subheader("Pebble Rate vs Time (SEP25)")
        fig3 = plot_pebble_rate_time()
        st.plotly_chart(fig3, use_container_width=True)
    elif selected_plot == "Cum Tons vs Time":
        st.subheader("Cumulative Tons vs Time (SEP25)")
        fig4 = plot_cumulative_tons_time()
        st.plotly_chart(fig4, use_container_width=True)
    elif selected_plot == "Fresh Feed vs Time":
        st.subheader("Fresh Feed vs Time (SEP25)")
        fig5 = plot_fresh_feed_time()
        st.plotly_chart(fig5, use_container_width=True)
    elif selected_plot == "Mill Runtime vs Time":
        st.subheader("Mill Runtime vs Time (SEP25)")
        fig6 = plot_mill_availability_time()
        st.plotly_chart(fig6, use_container_width=True)
    elif selected_plot == "Mill Load vs Time":
        st.subheader("Mill Load vs Time (SEP25 - Weekly Average)")
        fig7 = plot_mill_load_time()
        st.plotly_chart(fig7, use_container_width=True)
    elif selected_plot == "Mill Load vs Cum Tons":
        st.subheader("Mill Load vs Cumulative Tons")
        fig8 = plot_mill_load_cumtons()
        st.plotly_chart(fig8, use_container_width=True)
    elif selected_plot == "Power & Load vs Cum Tons":
        st.subheader("Mill Power & Load vs Cumulative Tons")
        fig9 = plot_mill_power_load_cumtons()
        st.plotly_chart(fig9, use_container_width=True)
    elif selected_plot == "Load vs Feed Rate":
        st.subheader("Mill Load vs Fresh Feed Rate")
        fig10 = plot_mill_load_vs_feed()
        st.plotly_chart(fig10, use_container_width=True)
    elif selected_plot == "Power vs Load":
        st.subheader("Mill Power vs Mill Load")
        fig11 = plot_mill_power_vs_load()
        st.plotly_chart(fig11, use_container_width=True)
    elif selected_plot == "Mill Filling vs CumFeed":
        st.subheader("Mill Filling vs Cumulative Feed")
        fig12 = plot_mill_filling_cumfeed()
        st.plotly_chart(fig12, use_container_width=True)
    elif selected_plot == "Silica vs CumFeed":  # Added new plot
        st.subheader("Silica vs Cumulative Feed")
        fig13 = plot_silica_cumfeed()
        st.plotly_chart(fig13, use_container_width=True)
    elif selected_plot == "Silica Timeseries":  # Added new plot
        st.subheader("Silica Timeseries (All Data)")
        fig14 = plot_silica_timeseries()
        st.plotly_chart(fig14, use_container_width=True)