import os
import pandas as pd

'''
"ID": "TRAM_T5_DIR1",
"STOPS": [
    "TRAM_T5_DIR1_EurexpoEntreePrinc",
    "TRAM_T5_DIR1_ParcduChene",
    "TRAM_T5_DIR1_LyceeJPSartre",
    "TRAM_T5_DIR1_DeTassignyCurial",
    "TRAM_T5_DIR1_LesAlizes",
    "TRAM_T5_DIR1_BronHoteldeVille",
    "TRAM_T5_DIR1_BoutasseCRousset",
    "TRAM_T5_DIR1_EssartsIris",
    "TRAM_T5_DIR1_Desgenettes",
    "TRAM_T5_DIR1_AmbroisePare",
    "TRAM_T5_DIR1_GrangeBlanche"
"TIMETABLE": [
    "07:51:00",
    "08:24:00",
    "08:51:00",
    "09:18:00",
    "09:45:00",
    "10:12:00",
    "10:39:00",
    "11:07:00",
    "11:21:00",
    "11:35:00",
    "11:50:00",
    "12:05:00",
    "12:20:00",
    "12:35:00",
    "12:50:00",
    "13:05:00",
    "13:20:00",
    "13:35:00",
    "13:50:00",
    "14:05:00",
    "14:20:00",
    "14:35:00",
    "14:50:00",
    "15:05:00",
    "15:20:00",
    "15:35:00",
    "15:50:00",
    "16:05:00",
    "16:20:00",
    "16:34:00",
    "16:55:00",
    "17:22:00",
    "18:22:00",
    "18:57:00",
    "19:11:00",
    "19:26:00",
    "19:40:00",
    "19:55:00",
    "20:10:00",
    "20:35:00",
    "21:00:00",
    "21:25:00"
],

"TRAM_T5_DIR1_EurexpoEntreePrinc": {
                "id": "TRAM_T5_DIR1_EurexpoEntreePrinc",
                "section": "TRAM_T5_DIR1_0_1",
                "relative_position": 0.0,
                "absolute_position": [
                    851476.2341540535,
                    6516588.599209512
                ]
            },
            "TRAM_T5_DIR1_ParcduChene": {
                "id": "TRAM_T5_DIR1_ParcduChene",
                "section": "TRAM_T5_DIR1_1_2",
                "relative_position": 0.0,
                "absolute_position": [
                    849798.1891833773,
                    6517323.901549733
                ]
            },
            "TRAM_T5_DIR1_LyceeJPSartre": {
                "id": "TRAM_T5_DIR1_LyceeJPSartre",
                "section": "TRAM_T5_DIR1_2_3",
                "relative_position": 0.0,
                "absolute_position": [
                    849454.2129249277,
                    6517203.322113191
                ]
            },
            "TRAM_T5_DIR1_DeTassignyCurial": {
                "id": "TRAM_T5_DIR1_DeTassignyCurial",
                "section": "TRAM_T5_DIR1_3_4",
                "relative_position": 0.0,
                "absolute_position": [
                    849058.4248550116,
                    6516941.538446901
                ]
            },
            "TRAM_T5_DIR1_LesAlizes": {
                "id": "TRAM_T5_DIR1_LesAlizes",
                "section": "TRAM_T5_DIR1_4_5",
                "relative_position": 0.0,
                "absolute_position": [
                    848897.174279685,
                    6516469.962891064
                ]
            },
'''

from pyproj import Transformer

def convert_corrdinates(row):
    return to_lambert93(row['ORIGIN']), to_lambert93(row['DESTINATION'])

def to_lambert93(coordinates):
    c = coordinates.split(' ')
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
    lat = c[0]
    lon = c[1]
    x, y = transformer.transform(lon, lat)
    return f'{x} {y}'
    # else:
    #     lat = c[0]
    #     lon = c[1]
    #     transformer = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
    #     lat, lon = transformer.transform(lat, lon)
    #     return f'{lat} {lon}'

if __name__ == '__main__':
    # Convert from lat/lon to Lambert-93
    coordinates = pd.DataFrame({'NAME': ['GrangeBlanche', 'TDeTassignyCurial', 'LyceeJPSartre', 'ParcduChene', 'Westfield', 'Bellecour', 'Confluances', 'Eurexpo'],
                                'COORD': ['45.742475491911755 4.879416016663879',
                                          '45.73572771803042 4.916971331306854',
                                          '45.73797438765062 4.922112189478452',
                                          '45.73898535652272 4.926770143919575',
                                          '45.76168877310396 4.856159993712235',
                                          '45.76078239352663, 4.834094344748039',
                                          '45.73362213384172 4.818299543365892',
                                          '45.73207539436152 4.947950762182816']})

    demandes = pd.DataFrame({'ID': ['U0', 'U1', 'U3'],
                             'DEPARTURE': ['08:20:00', '08:22:00', '08:22:00'],
                             'ORIGIN':  ['Eurexpo', 'ParcduChene', 'ParcduChene'],
                             'DESTINATION': ['GrangeBlanche', 'Bellecour', 'Confluances']
                             # 'ORIGIN': ['GrangeBlanche', 'GrangeBlanche', 'GrangeBlanche'],
                             # 'DESTINATION': ['ParcduChene', 'ParcduChene', 'ParcduChene']
                             })

    demandes = demandes.merge(coordinates, left_on=['ORIGIN'], right_on=['NAME'], how='left')
    demandes.drop(columns=['ORIGIN'], inplace=True)
    demandes.rename(columns={'COORD':'ORIGIN'}, inplace=True)

    demandes = demandes.merge(coordinates, left_on=['DESTINATION'], right_on=['NAME'], how='left')
    demandes.drop(columns=['DESTINATION', 'NAME_y'], inplace=True)
    demandes.rename(columns={'COORD': 'DESTINATION', 'NAME_x':'NAME'}, inplace=True)

    demandes[['ORIGIN', 'DESTINATION']] = demandes.apply(convert_corrdinates, axis=1, result_type='expand')

    print(demandes)
    demandes.drop(columns='NAME').to_csv('INPUTS/new_test_demands.csv', sep=';', index=False)



