import requests
import time as t
import pickle

with open('cor_dict.pickle', 'rb') as f:
    cor_dict = pickle.load(f)

with open('node_dict.pickle', 'rb') as f:
    node_dict = pickle.load(f)

with open('graph.pickle', 'rb') as f:
    graph = pickle.load(f)

# origin = '127.13144306487084, 37.44134209110179'
# des = '127.14112393388389, 37.44558371517034'


def distancAPI(origin, des) -> dict:
    query = {'origin': origin, 'destination': des, 'priority': 'DISTANCE', 'road_details': True}
    errCount = 0
    while True:
        try:
            response = requests.get("https://apis-navi.kakaomobility.com/v1/directions", params=query,  headers={'Authorization': 'KakaoAK 	?????', 'Content-Type': 'application/json'})
            myJson = response.json()
        except TimeoutError:
            print("CONNECTION ERR ..... retry after 30sec")
            t.sleep(30)
            errCount += 1
            if errCount > 10:
                raise KeyError("TimeOut!!")
            continue
        break

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


dist_matrix = [[0 for _ in range(7551)] for _ in range(7551)]
time_matrix = [[0 for _ in range(7551)] for _ in range(7551)]
road_matrix = [[None for _ in range(7551)] for _ in range(7551)]

for i in range(7550, -1, -1):
    for j in range(7550, -1, -1):
        if graph[i][j] == 1:
            start = ', '.join(map(str, node_dict[i+1][::-1]))
            end = ', '.join(map(str, node_dict[j+1][::-1]))

            try:
                distance, time, road_dist = distancAPI(start, end)  # raise KeyErr if fail
                print(i, j, distance, time, road_dist)
                dist_matrix[i][j] = distance
                time_matrix[i][j] = time
                road_matrix[i][j] = road_dist
            except KeyError:
                print("REQUEST FAILED...", i, j)
                with open("graphWeights.pickle", "wb") as fw:
                    pickle.dump(dist_matrix, fw)
                with open("time_matrix.pickle", "wb") as fw:
                    pickle.dump(time_matrix, fw)
                with open("road_matrix.pickle", "wb") as fw:
                    pickle.dump(road_matrix, fw)