import json
import pickle
from collections import OrderedDict
from typing import List, Dict

import pandas as pd
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

API_KEY = '...'

with open('cor_dict.pkl', 'rb') as f:
    COR_DICT = pickle.load(f)
with open('time_matrix.pkl', 'rb') as f:
    DISTANCE_MATRIX = pickle.load(f)
LON_GAP = 0.0033806626098715348 / 2
LAT_GAP = 0.0027283023109409563 / 2

# START_NODE = 5271  # 오산시 물류센터
START_NODE = 3630  # 화성시 물류센터


def ads_to_nodes(addresses: List[str]) -> Dict[int, List[int]]:
    """
    convert String addresses to the most appropriate Node numbers (nearest neighbour)
    :param addresses: list of String addresses
    :return: Dictionary of converted Node nums with address indexes
    """
    count = 1
    nodesWithAds = dict()

    adsWithCor = dict()

    for i, ad in enumerate(addresses):
        try:
            print(f'{count} addresses converted', end=' --> ')
            lat, lon = _getLatLng(ad)
            count += 1

            adsWithCor[i] = (lat, lon)

            for cor, node in COR_DICT.items():
                if cor[0] - LAT_GAP <= lat <= cor[0] + LAT_GAP and cor[1] - LON_GAP <= lon <= cor[1] + LON_GAP:
                    if node not in nodesWithAds:
                        nodesWithAds[node] = [i]
                    else:
                        nodesWithAds[node].append(i)
                    break

        except IndexError:
            print(f'wrong address format at index {i}:{ad}')
            continue
        except TypeError:
            print(f'wrong address format at index {i}:{ad}')
            continue
        except ConnectionError:
            print('### CONNECTION ERROR ###')
            break

    with open('adsWithCor.pkl', 'wb') as f:
        pickle.dump(adsWithCor, f, protocol=pickle.HIGHEST_PROTOCOL)

    return nodesWithAds


def _getLatLng(addr):
    url = 'https://dapi.kakao.com/v2/local/search/address.json?query=' + addr
    HEADER = {'Authorization': f'KakaoAK {API_KEY}', 'Content-Type': 'application/json'}
    result = json.loads(str(requests.get(url, headers=HEADER).text))
    status_code = requests.get(url, headers=HEADER).status_code
    if status_code != 200:
        raise ConnectionError(f"ERROR: Unable to call rest api, http_status_code: {status_code}")

    try:
        match_first = result['documents'][0]['address']

        lon: float = float(match_first['x'])
        lat: float = float(match_first['y'])
        print((lat, lon))
        return lat, lon
    except IndexError:  # match 값이 없을때
        raise IndexError(f"주소를 찾을수 없습니다\n정확한 주소를 입력해주세요 {addr}")
    except TypeError:  # match 값이 2개이상일때
        raise TypeError(f"하나이상의 좌표값이 리턴되었습니다\n정확한 주소를 입력해주세요 {addr}")


def nodeDistMatrix(today_nodes: List[int]):
    """
    extract n x n matrix from the distance_matrix
    n = today's delivery points
    :param today_nodes: today delivery nodes
    :return: today distance matrix (n x n), nodeCount: Dict[int, int]
    """
    nodeCount = OrderedDict()

    today_nodes = list(set(today_nodes))  # no duplicate
    today_nodes = list(map(lambda a: a - 1, today_nodes))  # 노드 번호 인덱스 값으로 변경
    today_nodes.sort()

    for element in sorted(list(set(today_nodes))):
        nodeCount[element+1] = today_nodes.count(element)

    today_nodes.insert(0, START_NODE - 1)  # 물류센터 노드를 시작 노드에 더함

    # today_matrix 작성
    today_matrix = []
    for i in range(len(today_nodes)):
        tmp = []
        for j in range(len(today_nodes)):
            tmp.append(DISTANCE_MATRIX[today_nodes[i]][today_nodes[j]])
        today_matrix.append(tmp)

    return today_matrix, nodeCount


def create_data_model(today_matrix, num_vehicles):
    """
    Stores the data for the problem
    :param today_matrix: n x n today_matrix
    :param num_vehicles: number of vehicles to be used in VRP
    :return: data dictionary
    """
    data = {'distance_matrix': today_matrix, 'num_vehicles': num_vehicles, 'depot': 0}
    return data


def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    max_route_distance = 0

    result = dict()

    for vehicle_id in range(data['num_vehicles']):
        result[vehicle_id] = []
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        while not routing.IsEnd(index):
            node_label = columns_list[manager.IndexToNode(index)]
            tmp = nodesWithAds[node_label] if node_label != START_NODE else [f'물류센터 {START_NODE}']

            if isinstance(tmp[0], int):
                result[vehicle_id].append(tmp[0])

            plan_output += ' {} -> '.format( tmp[0] )

            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        # plan_output += '{}\n'.format(manager.IndexToNode(index))
        plan_output += '{}\n'.format(f'물류센터 {START_NODE}')
        plan_output += 'Distance of the route: {} seconds\n'.format(route_distance)
        print(plan_output)
        max_route_distance = max(route_distance, max_route_distance)
    print('Maximum of the route distances: {} seconds'.format(max_route_distance))

    return result


def find_route(today_matrix, num_vehicles: int):
    """Entry point of the program."""
    # Instantiate the data problem.
    data = create_data_model(today_matrix, num_vehicles)

    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])

    # Create Routing Model.
    routing = pywrapcp.RoutingModel(manager)

    # Create and register a transit callback.
    def distance_callback(from_index, to_index):  # look up distance matrix
        """Returns the distance between the two nodes."""
        # Convert from routing variable Index to distance matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data['distance_matrix'][from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Distance constraint.
    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        300,  # 5 min each delivery
        28800,  # 근로기준법 1일 근로시간 = 8시간
        True,  # start cumul to zero
        dimension_name)
    distance_dimension = routing.GetDimensionOrDie(dimension_name)
    distance_dimension.SetGlobalSpanCostCoefficient(100)

    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        return print_solution(data, manager, routing, solution)
    else:
        print('No solution found !')
        return None


if __name__ == '__main__':
    df = pd.read_csv('sample_300.csv')
    ad_list: List[str] = df['받는분주소'].sample(n=100, random_state=1).values

    nodesWithAds: Dict[int, List[int]] = ads_to_nodes(ad_list)

    # with open('nodesWithAds.pkl', 'wb') as f:
    #     pickle.dump(nodesWithAds, f, protocol=pickle.HIGHEST_PROTOCOL)
    # with open('nodesWithAds.pkl', 'rb') as f:
    #     nodesWithAds = pickle.load(f)

    my_nodes = list(nodesWithAds.keys())
    node_matrix, nodeCount = nodeDistMatrix(my_nodes)  # nodeCount: OrderedDict[int, int]

    columns_list = list(nodeCount.keys())
    columns_list.insert(0, START_NODE)  # [START_NODE, ........ nodes ...........]

    result = find_route(node_matrix, 5)
    with open('result.txt', 'wt') as f:
        for key, item in result.items():
            f.write(f'vehicle {key}\n')
            f.write(f'물류센터 {START_NODE}, ')

            for ad in item:
                f.write(f'\'{ad_list[ad]}\', ')
            f.write(f'물류센터 {START_NODE}\n')
