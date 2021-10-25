import json
import pickle
from typing import List

import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# API_KEY_LIST = ['62e08eb099c720a9a6b8ce429285b169', 'a11962d0038edfb6f73799c64cf008db',
#                 'af39952532715711ee099595385810d0', 'fd8116edb66e85eabf70a3bd1de826d4',
#                 'caefff050a36c52cbc463eab75b6a31d', '7a57f2b24d51a22d76d3f9df996a1a98',
#                 '68666720352f90cec83ad6691b3777e3', 'f0db6152b170ce7b5bec9a29aee71597']
API_KEY = '62e08eb099c720a9a6b8ce429285b169'

with open('cor_dict.pkl', 'rb') as f:
    COR_DICT = pickle.load(f)
with open('time_matrix.pkl', 'rb') as f:
    DISTANCE_MATRIX = pickle.load(f)
LON_GAP = 0.0033806626098715348 / 2
LAT_GAP = 0.0027283023109409563 / 2


def ads_to_nodes(addresses: List[str]) -> List[int]:
    """
    convert String addresses to the most appropriate Node numbers (nearest neighbour)
    :param addresses: list of String addresses
    :return: list of converted Node nums
    """
    count = 1
    nodeList = []
    for i, ad in enumerate(addresses):
        try:
            print(f'{count} addresses converted', end=' --> ')
            lat, lon = _getLatLng(ad)
            count += 1
            for cor, node in COR_DICT.items():
                if cor[0] - LAT_GAP <= lat <= cor[0] + LAT_GAP and cor[1] - LON_GAP <= lon <= cor[1] + LON_GAP:
                    nodeList.append(node)
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

    return nodeList


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


def nodeDistMatrix(today_nodes: List[int]) -> List[List[float]]:
    """
    extract n x n matrix from the distance_matrix
    n = today's delivery points
    :param today_nodes: today delivery nodes
    :return: today distance matrix (n x n)
    """
    today_nodes = list(map(lambda a: a - 1, today_nodes))  # 노드 번호 인덱스 값으로 변경
    today_nodes.sort()
    today_nodes.insert(0, today_nodes.pop(today_nodes.index(5270)))  # 물류센터 노드를 시작 노드로 설정

    # today_matrix 작성
    today_matrix = []
    for i in range(len(today_nodes)):
        tmp = []
        for j in range(len(today_nodes)):
            tmp.append( DISTANCE_MATRIX[today_nodes[i]][today_nodes[j]] )
        today_matrix.append(tmp)

    return today_matrix


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
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        route_distance = 0
        while not routing.IsEnd(index):
            plan_output += ' {} -> '.format(manager.IndexToNode(index))
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            route_distance += routing.GetArcCostForVehicle(
                previous_index, index, vehicle_id)
        plan_output += '{}\n'.format(manager.IndexToNode(index))
        plan_output += 'Distance of the route: {}m\n'.format(route_distance)
        print(plan_output)
        max_route_distance = max(route_distance, max_route_distance)
    print('Maximum of the route distances: {}m'.format(max_route_distance))


def main(today_matrix, num_vehicles: int):
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
        0,  # no slack
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
        print_solution(data, manager, routing, solution)
    else:
        print('No solution found !')


if __name__ == '__main__':
    # ad_list = [...]
    # node_list = ads_to_nodes(ad_list)

    f = open('test_node_list.pkl', 'r')
    TEST_NODE_LIST = pickle.load(f)
    f.close()

    dist_matrix = nodeDistMatrix(TEST_NODE_LIST)
    main(dist_matrix, 86)
