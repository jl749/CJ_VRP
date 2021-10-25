import requests
import pickle
import json

with open('cor_dict.pkl', 'rb') as f:
    cor_dict = pickle.load(f)

with open('node_dict.pkl', 'rb') as f:
    node_dict = pickle.load(f)

with open('graph.pkl', 'rb') as f:
    graph = pickle.load(f)

# 신하섬 62e08eb099c720a9a6b8ce429285b169
# 강병국 a11962d0038edfb6f73799c64cf008db
# 강태환 af39952532715711ee099595385810d0
# 이정무 caefff050a36c52cbc463eab75b6a31d
# 천영성 7a57f2b24d51a22d76d3f9df996a1a98
# 전세현 fd8116edb66e85eabf70a3bd1de826d4

API_KEY_LIST = ['62e08eb099c720a9a6b8ce429285b169', 'a11962d0038edfb6f73799c64cf008db',
                'af39952532715711ee099595385810d0', 'fd8116edb66e85eabf70a3bd1de826d4',
                'caefff050a36c52cbc463eab75b6a31d', '7a57f2b24d51a22d76d3f9df996a1a98',
                '68666720352f90cec83ad6691b3777e3', 'f0db6152b170ce7b5bec9a29aee71597']
INDEX = 0

f = open('API_LOG.txt', 'w')


def distancAPI(origin, des) -> dict:
    query = {'origin': origin, 'destination': des, 'priority': 'DISTANCE', 'road_details': True}

    HEADER = {'Authorization': f'KakaoAK {API_KEY_LIST[INDEX]}', 'Content-Type': 'application/json'}
    response = requests.get("https://apis-navi.kakaomobility.com/v1/directions", params=query, headers=HEADER)
    myJson = response.json()

    resultCode = myJson['routes'][0]['result_code']  # raise keyerr
    if resultCode != 0:
        print(resultCode, end="...")
        return float("inf"), float("inf"), dict()
    distance = myJson['routes'][0]['summary']['distance']
    time = myJson['routes'][0]['summary']['duration']

    roads = myJson['routes'][0]['sections'][0]['roads']
    road_dist = dict()
    for road in roads:
        if not road['name']:  # if name empty
            continue
        if road['name'] in road_dist:
            road_dist[road['name']] += road['distance']
        else:
            road_dist[road['name']] = road['distance']
    return distance, time, road_dist


weighted_graph = [[0 for _ in range(7551)] for _ in range(7551)]
time_matrix = [[0 for _ in range(7551)] for _ in range(7551)]
road_matrix = [[None for _ in range(7551)] for _ in range(7551)]

flag = 0
for i in range(7550, -1, -1):
    if flag == 1:
        break
    for j in range(7550, -1, -1):
        if flag == 1:
            break
        if graph[i][j] == 1:
            start = ', '.join(map(str, node_dict[i + 1][::-1]))
            end = ', '.join(map(str, node_dict[j + 1][::-1]))

            while True:
                try:
                    distance, time, road_dist = distancAPI(start, end)  # throw KeyErr if fail
                    print(i, j, distance, time, road_dist)

                    myRoad: str = json.dumps(road_dist) if len(road_dist) else '{}'
                    f.write(f"{i}, {j}, {distance}, {time}, {myRoad}\n")
                    f.flush()

                    weighted_graph[i][j] = distance
                    time_matrix[i][j] = time
                    road_matrix[i][j] = road_dist
                except KeyError:
                    print("REQUEST FAILED...", i, j)
                    f.write(f"REQUEST FAILED at {i}, {j}\n")
                    f.flush()
                    print("----------------------")
                    INDEX = INDEX + 1 if INDEX < 8 else INDEX
                    if INDEX > 7:  # if 8
                        flag = 1
                        break
                    continue
                break

with open("distanceWeightedGraph.pkl", "wb") as fw:
    pickle.dump(weighted_graph, fw)
with open("timeWeightedGraph.pkl", "wb") as fw:
    pickle.dump(time_matrix, fw)
with open("road_matrix.pkl", "wb") as fw:
    pickle.dump(road_matrix, fw)
f.close()
