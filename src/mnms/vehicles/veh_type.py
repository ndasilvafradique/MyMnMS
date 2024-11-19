# from abc import ABC, abstractmethod
# from collections import deque
# from copy import deepcopy
# from typing import List, Tuple, Deque, Optional, Generator, Callable
# from enum import Enum
# from dataclasses import dataclass, field
# import queue, random
#
# import numpy as np
#
# from mnms.tools.observer import TimeDependentSubject
# from mnms.log import create_logger
# from mnms.time import Time, Dt
#
# log = create_logger(__name__)
# _norm = np.linalg.norm
#
# _TYPE_ITEM_PATH = Tuple[Tuple[str, str], float]
# _TYPE_PATH = List[_TYPE_ITEM_PATH]
#
#
# def will_be_selected(q, item):
#
#     N = len(q)
#     pos = q.index(item)
#     """
#     Calculates probabilities for each position in a queue of length N.
#     """
#     if N == 1:
#         return True
#     else:
#         p = 1 - (pos - 1) / (N - 1)
#         return p >= 0.5
#
# class ActivityType(Enum):
#     """Enumerate activity types."""
#
#     STOP = 0
#     REPOSITIONING = 1
#     PICKUP = 2
#     SERVING = 3
#
#
# @dataclass(slots=True)
# class VehicleActivity(ABC):
#     """Class representing a vehicle activity.
#
#         Attributes:
#             activity_type (ActivityType): the type of the activity
#             is_moving (bool): indicates if the vehicle moves or not during the activity
#             node (str): the ID of the node (linked to the activity type)
#             path (_TYPE_PATH): the path linked to the activity
#             user: the user linked to the activity
#             is_done: indicates if the activity is terminated
#             iter_path: the iterator of the path
#
#     """
#     activity_type: ActivityType
#     is_moving: bool
#
#     node: str
#     path: _TYPE_PATH = field(default_factory=list)
#     iter_path: Generator[_TYPE_ITEM_PATH, None, None] = field(default=None, init=False)
#
#     user: "User" = None
#
#     is_done: bool = False
#
#     def __post_init__(self):
#         self.reset_path_iterator()
#
#     def reset_path_iterator(self):
#         self.iter_path = iter(self.path)
#
#     def modify_path(self, new_path: _TYPE_PATH):
#         """Method to update this activity path.
#
#         Args:
#             -new_path: the new path
#         """
#         self.path = new_path
#         if new_path:
#             self.node = new_path[-1][0][1]
#         self.reset_path_iterator()
#
#     def modify_path_and_next(self, new_path: _TYPE_PATH):
#         """Method to update this activity path and set the iterator on path to the next node.
#
#         Args:
#             -new_path: the new path
#         """
#         self.modify_path(new_path)
#         next(self.iter_path)
#
#     @abstractmethod
#     def done(self, veh: "Vehicle", tcurrent: Time):
#         """Update when the activity is done (abstract method)
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#
#         return
#
#     @abstractmethod
#     def start(self, veh: "Vehicle"):
#         """Update when the activity is started (abstract method)
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activity
#         """
#
#         return
#
#     def copy(self):
#         return self.__class__(deepcopy(self.node),
#                               deepcopy(self.path),
#                               self.user,
#                               self.is_done)
#
#
# @dataclass(slots=True)
# class VehicleActivityStop(VehicleActivity):
#     """Class representing a no activity."""
#
#     activity_type: ActivityType = field(default=ActivityType.STOP, init=False)
#     is_moving: bool = field(default=False, init=False)
#
#     def start(self, veh: "Vehicle"):
#         """Update when the activity is started
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#
#         return
#
#     def done(self, veh: "Vehicle", tcurrent: Time):
#         """Update when the activity is done
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#         '''non saprei onestamente, perche' come faccio a dedurre se l'utente debba scendere o salire?'''
#         if veh.is_public_transport():
#             if self.user is not None:
#                 if not self.user.is_in_vehicle:
#                     if self.user.id not in veh.waiting_queue:
#                         veh.waiting_queue.append(self.user.id)
#                         self.user.set_state_waiting_vehicle(veh)
#                 print('Stop done', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}', veh.waiting_queue)
#         else:
#             '''non me lo spiego'''
#             if self.user is not None:
#                 self.user.vehicle = veh
#
#
# @dataclass(slots=True)
# class VehicleActivityRepositioning(VehicleActivity):
#     """Class representing a repositionning activity."""
#
#     activity_type: ActivityType = field(default=ActivityType.REPOSITIONING, init=False)
#     is_moving: bool = field(default=True, init=False)
#
#     def start(self, veh: "Vehicle"):
#         """Update when the activity is started
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#
#         return
#
#     def done(self, veh: "Vehicle", tcurrent: Time):
#         """Update when the activity is done
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#
#         return
#
#
# @dataclass(slots=True)
# class VehicleActivityPickup(VehicleActivity):
#     """Class representing a pick-up activity."""
#     activity_type: ActivityType = field(default=ActivityType.PICKUP, init=False)
#     is_moving: bool = field(default=True, init=False)
#
#     def start(self, veh: "Vehicle"):
#         """Update when the activity is started
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#         '''Dato che pickup può essere eseguito anche dopo serving, assicuriamoci che l'utente non sia già nella coda'''
#         if veh.is_public_transport():
#             if self.user.id not in veh.waiting_queue:
#                 '''Se non è nella coda, aggiungiamolo e cambiamo il suo stato'''
#                 self.user.set_state_waiting_vehicle(veh)
#                 veh.waiting_queue.append(self.user.id)
#                 print('Pickup start', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}', veh.waiting_queue)
#         else:
#             self.user.set_state_waiting_vehicle(veh)
#             print('Pickup start', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}', veh.waiting_queue)
#
#     def done(self, veh: "Vehicle", tcurrent: Time):
#         """Update when the activity is done
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#         if veh.is_public_transport():
#             '''Controlliamo se il numero di passeggeri nel veicolo più quello che ci vorrebbe salire,
#             è al di sotto della capacità del veicolo...'''
#             can_pickup = False
#             if len(veh.passengers) + 1 <= veh.capacity:
#                 '''... se la coda è vuota oppure se ci sono persone in attesa e l'utente è il primo della lista,
#                 potrà salire (⁜)'''
#                 if (len(veh.waiting_queue) == 0 or
#                         (not len(veh.waiting_queue) == 0 and will_be_selected(veh.waiting_queue, self.user.id))):
#                     can_pickup = True
#
#             '''Se, al termine dei controlli, è possibile accogliere l'utente, gli assegniamo il veicolo,
#             cambiamo stato e lo togliamo dalla coda'''
#             if can_pickup:
#                 self.user.vehicle = veh
#                 veh.passengers[self.user.id] = self.user
#                 self.user.set_state_inside_vehicle()
#                 self.user.notify(tcurrent)
#                 '''Questo controllo è necessario altrimenti la coda si bloccherà in attesa di avere un elemento disponibile'''
#                 if not len(veh.waiting_queue) == 0 and will_be_selected(veh.waiting_queue, self.user.id):
#                     veh.waiting_queue.remove(self.user.id)
#                     '''Il controllo è sufficiente perchè se la coda è vuota, è il primo a salire.
#                     Altrimenti, se la coda non è vuota, ma can_pickup è true,
#                     la seconda parte di (⁜) è necessariamente vera. Quindi sicuramente è il primo.'''
#                 print('Pickup done', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}', veh.waiting_queue)
#         else:
#             self.user.vehicle = veh
#             veh.passengers[self.user.id] = self.user
#             self.user.set_state_inside_vehicle()
#             self.user.notify(tcurrent)
#             print('Pickup done', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}', veh.waiting_queue)
#
#
# @dataclass(slots=True)
# class VehicleActivityServing(VehicleActivity):
#     """Class representing a serving activity."""
#     activity_type: ActivityType = field(default=ActivityType.SERVING, init=False)
#     is_moving: bool = field(default=True, init=False)
#
#     def start(self, veh: "Vehicle"):
#         """Update when the activity is started
#
#             Parameters:
#                 veh (Vehicle): The vehicle performing the activities
#         """
#         if veh.is_public_transport():
#             can_serve = False
#             '''Se l'utente è già nel veicolo, a causa di un precedente pickup, non serve fare serving'''
#             if not self.user.is_in_vehicle:
#                 '''Se la coda e' vuota, oppure lui e' il primo in attesa, servilo'''
#                 if len(veh.waiting_queue) == 0 or (not len(veh.waiting_queue) == 0 and will_be_selected(veh.waiting_queue, self.user.id)):
#                     can_serve = True
#                 ### FOR CHRISTOPHE: i am not sure if I need to add this control, because I don't know if serving start and serving done can be performed sequentially or not
#                 elif self.user.id not in veh.waiting_queue:
#                     '''altrimenti, se non stava nella coda, mettilo in lista'''
#                     veh.waiting_queue.append(self.user.id)
#
#             if can_serve:
#                 ### FOR CHRISTOPHE: i am not sure if I need to add this control, because I don't know if serving start and serving done can be performed sequentially or not
#                 '''Se si trovava nella coda va rimosso'''
#                 if len(veh.waiting_queue) == 0 and will_be_selected(veh.waiting_queue, self.user.id):
#                     self.user.vehicle = veh
#                     veh.passengers[self.user.id] = self.user
#                     self.user.set_state_inside_vehicle()
#                     ### REMOVING THE USER FROM THE WAITING QUEUE SHOULD BE DONE ONLY IN THE DONE SERVING, BUT I DON'T KNOW IF IT SUFFICIENT
#                     veh.waiting_queue.remove(self.user.id)
#                 print('Serving start', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}', veh.waiting_queue)
#
#         else:
#             self.user.vehicle = veh
#             veh.passengers[self.user.id] = self.user
#             self.user.set_state_inside_vehicle()
#             print('Serving start', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}', veh.waiting_queue)
#
#     def done(self, veh: "Vehicle", tcurrent: Time):
#         """Update when the activity is done
#
#              Parameters:
#                  veh (Vehicle): The vehicle performing the activities
#          """
#         '''Se l'utente e' un passeggero di un trasporto pubblico ed e' il primo della lista nella coda, deve salire sul mezzo'''
#         if self.user.id in veh.passengers:
#             if veh.is_public_transport() and not len(veh.waiting_queue) == 0:
#                 veh.waiting_queue.remove(self.user.id)
#             self.user.vehicle = None
#             veh.passengers.pop(self.user.id)
#             print('Serving done', veh.type, veh.id, f'{len(veh.passengers)}/{veh.capacity}')
#             self.user.remaining_link_length = 0
#             upath = self.user.path.nodes
#             last_achieved = False
#             if veh._current_link is not None:
#                 if veh._current_link[1] == veh._current_node and self.user.achieved_path and veh._current_node == \
#                         self.user.achieved_path[-1]:
#                     last_achieved = True
#                 unode = veh._current_link[1]
#             else:
#                 unode = veh._current_node
#             next_node_ind = self.user.get_node_index_in_path(unode, last_achieved=last_achieved) + 1
#             self.user.set_position((unode, upath[next_node_ind]), unode, 0, veh.position, tcurrent)
#             self.user.update_achieved_path_ms(veh.mobility_service)
#             self.user.vehicle = None
#             self.user.set_state_stop()
#             self.user.notify(tcurrent)
#             # If this is user's personal vehicle, register location of parking and vehicle's mobility service
#             # on user's side and last dropped off user on vehicle's side to prevent deletion of personal vehicle
#             # before user's arrival at destination
#             if veh._is_personal:
#                 self.user.park_personal_vehicle(veh.mobility_service, unode)
#                 veh.last_dropped_off_user = self.user
#
#
# class Vehicle(TimeDependentSubject):
#     _counter = 0
#
#     def __init__(self,
#                  node: str,
#                  capacity: int,
#                  mobility_service: str,
#                  is_personal: bool,
#                  activities: Optional[List[VehicleActivity]] = None):
#         """
#         Class representing a vehicle in the simulation
#
#         Args:
#             node: The node where the Vehicle is created
#             capacity: the capacity of the Vehicle
#             mobility_service: The associated mobility service
#             activities: The initial activities of the Vehicle
#             is_personal: Boolean specifying if the vehicle is personal or not
#         """
#
#         super(Vehicle, self).__init__()
#
#         self.waiting_queue = []
#         self._global_id = str(Vehicle._counter)
#         Vehicle._counter += 1
#
#         self._capacity = capacity
#         self.mobility_service = mobility_service
#         self._is_personal = is_personal
#
#         self.passengers = dict()  # id_user, user
#
#         self._current_link = None
#         self._current_node = node
#         self._remaining_link_length = None
#         self._position = None  # current vehicle coordinates
#         self._distance = 0  # travelled distance ( reset to zero if other trip ?)
#         self._distance_at_last_res_change = 0  # distance this vehicle has traveled since it enters current reservoir
#         self._iter_path = None
#         self.speed = None  # current speed
#         self._dt_move = None
#         self._achieved_path = []
#         self._achieved_path_since_last_notify = []
#
#         self.activities: Deque[VehicleActivity] = deque([])
#         self.activity = None  # current activity
#
#         if activities is not None:
#             self.add_activities(activities)
#             self.next_activity(None)
#         else:
#             self.activity: VehicleActivity = self.default_activity()
#
#     def __repr__(self):
#         return f"{self.__class__.__name__}('{self._global_id}', '{self.activity_type.name if self.activity_type is not None else None}')"
#
#     @property
#     def distance(self):
#         return self._distance
#
#     @property
#     def distance_at_last_res_change(self):
#         return self._distance_at_last_res_change
#
#     @distance_at_last_res_change.setter
#     def distance_at_last_res_change(self, d):
#         self._distance_at_last_res_change = d
#
#     @property
#     def is_full(self):
#         return len(self.passengers) >= self._capacity
#
#     @property
#     def capacity(self):
#         return self._capacity
#
#     @property
#     def is_empty(self):
#         return not bool(self.passengers)
#
#     @property
#     def id(self):
#         return self._global_id
#
#     @property
#     def type(self):
#         return self.__class__.__name__
#
#     @property
#     def current_link(self):
#         return self._current_link
#
#     @property
#     def current_node(self):
#         return self._current_node
#
#     @property
#     def remaining_link_length(self):
#         return self._remaining_link_length
#
#     @property
#     def position(self):
#         return self._position
#
#     @property
#     def activity_type(self) -> ActivityType:
#         return self.activity.activity_type if self.activity is not None else None
#
#     @property
#     def is_moving(self) -> bool:
#         return self.activity.is_moving if self.activity is not None else False
#
#     @property
#     def dt_move(self) -> Dt:
#         return self._dt_move
#
#     @dt_move.setter
#     def dt_move(self, dt):
#         self._dt_move = dt
#
#     @property
#     def achieved_path(self):
#         return self._achieved_path
#
#     def is_public_transport(self):
#         return True if self.mobility_service.upper() in ['BUS', 'TRAM', 'METRO'] else False
#
#     def update_achieved_path(self):
#         if len(self.achieved_path) == 0 or self.current_node != self.achieved_path[-1]:
#             self._achieved_path.append(self.current_node)
#             self._achieved_path_since_last_notify.append(self.current_node)
#
#     def flush_achieved_path_since_last_notify(self):
#         self._achieved_path_since_last_notify = []
#
#     def add_activities(self, activities: List[VehicleActivity]):
#         for a in activities:
#             self.activities.append(a)
#
#     def next_activity(self, tcurrent: Time):
#         if self.activity is not None:
#             self.activity.done(self, tcurrent)
#
#         try:
#             activity = self.activities.popleft()
#         except IndexError:
#             activity = self.default_activity()
#
#         self.activity = activity
#         self.activity.start(self)
#         if activity.activity_type is not ActivityType.STOP:
#             if activity.path:
#                 self._current_link, self._remaining_link_length = next(activity.iter_path)
#                 assert self._current_node == self._current_link[
#                     0], f"Veh {self.id} current node {self._current_node} is not equal to the next upstream link {self._current_link[0]}"
#             else:
#                 activity.is_done = True
#
#     def override_current_activity(self):
#         next_activity = self.activities.popleft()
#         last_activity = self.activity
#         self.activity = next_activity
#         self.activity.start(self)
#
#         if last_activity.activity_type is ActivityType.STOP:
#             if next_activity.path:
#                 self._current_link, self._remaining_link_length = next(next_activity.iter_path)
#                 assert self._current_node == self._current_link[0]
#             else:
#                 next_activity.is_done = True
#
#     def iter_activities(self):
#         yield self.activity
#         for act in self.activities:
#             yield act
#
#     def set_path(self, path: List[Tuple[Tuple[str, str], float]]):
#         self._iter_path = iter(path)
#         self._current_link, self._remaining_link_length = next(self._iter_path)
#
#     def update_distance(self, dist: float):
#         self._distance += dist
#         for user in self.passengers.values():
#             user.update_distance(dist)
#
#     def set_position(self, position: np.ndarray):
#         self._position = position
#
#     def drop_user(self, tcurrent: Time, user: 'User', drop_pos: np.ndarray):
#         log.info(f"{user} is dropped at {self._current_link[0]}")
#         user.remaining_link_length = 0
#         upath = user.path.nodes
#         unode = self._current_link[0]
#         next_node_ind = user.get_node_index_in_path(unode) + 1
#         user.set_position((unode, upath[next_node_ind]), unode, 0, drop_pos, tcurrent)
#         user.vehicle = None
#         user.notify(tcurrent)
#
#         del self.passengers[user.id]
#
#     def drop_all_passengers(self, tcurrent: Time):
#         for _, user in self.passengers.values():
#             log.info(f"{user} is dropped at {self._current_link[1]}")
#             unode = self._current_link[1]
#             user.current_node = unode
#             user.remaining_link_length = 0
#             user.position = self._position
#             user.notify(tcurrent)
#             user.vehicle = None
#
#         self.passengers = dict()
#
#     def start_user_trip(self, userid, take_node):
#         log.info(f'Passenger {userid} has been taken by {self} at {take_node}')
#         take_time, user = self._next_passenger.pop(userid)
#         user.vehicle = self.id
#         self.passengers[userid] = (take_time, user)
#
#     def default_activity(self):
#         return VehicleActivityStop(node=self._current_node,
#                                    path=[],
#                                    is_done=False)
#
#     def notify_passengers(self, tcurrent: Time):
#         for user in self.passengers.values():
#             user.notify(tcurrent)
#
#     def path_to_nodes(self, path):
#         """Method that converts a VehicleActivity path into a list of nodes.
#
#         Args:
#             -path: path to convert
#
#         Returns:
#             -path_nodes: the converted path
#         """
#         if len(path) > 0:
#             path_nodes = [l[0][0] for l in path] + [path[-1][0][1]]
#         else:
#             path_nodes = [self._current_node]
#         return path_nodes
#
#     @classmethod
#     def reset_counter(cls):
#         cls._counter = 0
#
#
# class Car(Vehicle):
#     def __init__(self,
#                  node: str,
#                  capacity: int,
#                  mobility_service: str,
#                  is_personal: bool,
#                  activities: Optional[VehicleActivity] = None):
#         super(Car, self).__init__(node, capacity, mobility_service, is_personal, activities)
#         self._last_dropped_off_user = None
#
#     @property
#     def last_dropped_off_user(self):
#         return self._last_dropped_off_user
#
#     @last_dropped_off_user.setter
#     def last_dropped_off_user(self, user):
#         self._last_dropped_off_user = user
#
#
# class Bus(Vehicle):
#     def __init__(self,
#                  node: str,
#                  capacity: int,
#                  mobility_service: str,
#                  is_personal: bool = False,
#                  activities: Optional[VehicleActivity] = None):
#         super(Bus, self).__init__(node, capacity, mobility_service, is_personal, activities)
#
#
# class Tram(Vehicle):
#     def __init__(self,
#                  node: str,
#                  capacity: int,
#                  mobility_service: str,
#                  is_personal: bool = False,
#                  activities: Optional[VehicleActivity] = None):
#         super(Tram, self).__init__(node, capacity, mobility_service, is_personal, activities)
#
#
# class Metro(Vehicle):
#     def __init__(self,
#                  node: str,
#                  capacity: int,
#                  mobility_service: str,
#                  is_personal: bool = False,
#                  activities: Optional[VehicleActivity] = None):
#         super(Metro, self).__init__(node, capacity, mobility_service, is_personal, activities)
#
#
# class Bike(Vehicle):
#     def __init__(self,
#                  node: str,
#                  capacity: int,
#                  mobility_service: str,
#                  is_personal: bool,
#                  activities: Optional[VehicleActivity] = None):
#         capacity = 1
#         super(Bike, self).__init__(node, capacity, mobility_service, is_personal, activities)
#
#
# class Train(Vehicle):
#     def __init__(self,
#                  node: str,
#                  capacity: int,
#                  mobility_service: str,
#                  is_personal: bool = False,
#                  activities: Optional[VehicleActivity] = None):
#         super(Train, self).__init__(node, capacity, mobility_service, is_personal, activities)


'''ORIGINAL VERSION '''

from abc import ABC, abstractmethod
from collections import deque
from copy import deepcopy
from typing import List, Tuple, Deque, Optional, Generator, Callable
from enum import Enum
from dataclasses import dataclass, field

import numpy as np

from mnms.tools.observer import TimeDependentSubject
from mnms.log import create_logger
from mnms.time import Time, Dt

log = create_logger(__name__)
_norm = np.linalg.norm

_TYPE_ITEM_PATH = Tuple[Tuple[str, str], float]
_TYPE_PATH = List[_TYPE_ITEM_PATH]

class ActivityType(Enum):
    """Enumerate activity types."""

    STOP = 0
    REPOSITIONING = 1
    PICKUP = 2
    SERVING = 3


@dataclass(slots=True)
class VehicleActivity(ABC):
    """Class representing a vehicle activity.

        Attributes:
            activity_type (ActivityType): the type of the activity
            is_moving (bool): indicates if the vehicle moves or not during the activity
            node (str): the ID of the node (linked to the activity type)
            path (_TYPE_PATH): the path linked to the activity
            user: the user linked to the activity
            is_done: indicates if the activity is terminated
            iter_path: the iterator of the path

    """
    activity_type: ActivityType
    is_moving: bool

    node: str
    path: _TYPE_PATH = field(default_factory=list)
    iter_path: Generator[_TYPE_ITEM_PATH, None, None] = field(default=None, init=False)

    user: "User" = None

    is_done: bool = False

    def __post_init__(self):
        self.reset_path_iterator()

    def reset_path_iterator(self):
        self.iter_path = iter(self.path)

    def modify_path(self, new_path: _TYPE_PATH):
        """Method to update this activity path.

        Args:
            -new_path: the new path
        """
        self.path = new_path
        if new_path:
            self.node = new_path[-1][0][1]
        self.reset_path_iterator()

    def modify_path_and_next(self, new_path: _TYPE_PATH):
        """Method to update this activity path and set the iterator on path to the next node.

        Args:
            -new_path: the new path
        """
        self.modify_path(new_path)
        next(self.iter_path)

    @abstractmethod
    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done (abstract method)

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return

    @abstractmethod
    def start(self, veh: "Vehicle"):
        """Update when the activity is started (abstract method)

            Parameters:
                veh (Vehicle): The vehicle performing the activity
        """

        return

    def copy(self):
        return self.__class__(deepcopy(self.node),
                              deepcopy(self.path),
                              self.user,
                              self.is_done)


@dataclass(slots=True)
class VehicleActivityStop(VehicleActivity):
    """Class representing a no activity."""

    activity_type: ActivityType = field(default=ActivityType.STOP, init=False)
    is_moving: bool = field(default=False, init=False)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        if self.user is not None:
            self.user.vehicle = veh


@dataclass(slots=True)
class VehicleActivityRepositioning(VehicleActivity):
    """Class representing a repositionning activity."""

    activity_type: ActivityType = field(default=ActivityType.REPOSITIONING, init=False)
    is_moving: bool = field(default=True, init=False)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return


@dataclass(slots=True)
class VehicleActivityPickup(VehicleActivity):
    """Class representing a pick-up activity."""
    activity_type: ActivityType = field(default=ActivityType.PICKUP, init=False)
    is_moving: bool = field(default=True, init=False)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        self.user.set_state_waiting_vehicle(veh)

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        self.user.vehicle = veh
        veh.passengers[self.user.id] = self.user
        self.user.set_state_inside_vehicle()


@dataclass(slots=True)
class VehicleActivityServing(VehicleActivity):
    """Class representing a serving activity."""
    activity_type: ActivityType = field(default=ActivityType.SERVING, init=False)
    is_moving: bool = field(default=True, init=False)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """
        self.user.vehicle = veh
        veh.passengers[self.user.id] = self.user
        self.user.set_state_inside_vehicle()

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

             Parameters:
                 veh (Vehicle): The vehicle performing the activities
         """
        self.user.vehicle = None
        veh.passengers.pop(self.user.id)

        self.user.remaining_link_length = 0
        upath = self.user.path.nodes
        last_achieved = False
        if veh._current_link is not None:
            if veh._current_link[1] == veh._current_node and self.user.achieved_path and veh._current_node == self.user.achieved_path[-1]:
                last_achieved = True
            unode = veh._current_link[1]
        else:
            unode = veh._current_node
        next_node_ind = self.user.get_node_index_in_path(unode, last_achieved=last_achieved) + 1
        self.user.set_position((unode, upath[next_node_ind]), unode, 0, veh.position, tcurrent)
        self.user.update_achieved_path_ms(veh.mobility_service)
        self.user.vehicle = None
        # self.user.notify(tcurrent)
        self.user.set_state_stop()
        # If this is user's personal vehicle, register location of parking and vehicle's mobility service
        # on user's side and last dropped off user on vehicle's side to prevent deletion of personal vehicle
        # before user's arrival at destination
        if veh._is_personal:
            self.user.park_personal_vehicle(veh.mobility_service, unode)
            veh.last_dropped_off_user = self.user


class Vehicle(TimeDependentSubject):

    _counter = 0

    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool,
                 activities: Optional[List[VehicleActivity]] = None):
        """
        Class representing a vehicle in the simulation

        Args:
            node: The node where the Vehicle is created
            capacity: the capacity of the Vehicle
            mobility_service: The associated mobility service
            activities: The initial activities of the Vehicle
            is_personal: Boolean specifying if the vehicle is personal or not
        """

        super(Vehicle, self).__init__()

        self._global_id = str(Vehicle._counter)
        Vehicle._counter += 1

        self._capacity = capacity
        self.mobility_service = mobility_service
        self._is_personal = is_personal

        self.passengers = dict()                     # id_user, user

        self._current_link = None
        self._current_node = node
        self._remaining_link_length = None
        self._position = None                       # current vehicle coordinates
        self._distance = 0                          # travelled distance ( reset to zero if other trip ?)
        self._distance_at_last_res_change = 0       # distance this vehicle has traveled since it enters current reservoir
        self._iter_path = None
        self.speed = None                           # current speed
        self._dt_move = None
        self._achieved_path = []
        self._achieved_path_since_last_notify = []

        self.activities: Deque[VehicleActivity] = deque([])
        self.activity = None                        # current activity

        if activities is not None:
            self.add_activities(activities)
            self.next_activity(None)
        else:
            self.activity: VehicleActivity = self.default_activity()

    def __repr__(self):
        return f"{self.__class__.__name__}('{self._global_id}', '{self.activity_type.name if self.activity_type is not None else None}')"

    @property
    def distance(self):
        return self._distance

    @property
    def distance_at_last_res_change(self):
        return self._distance_at_last_res_change

    @distance_at_last_res_change.setter
    def distance_at_last_res_change(self, d):
        self._distance_at_last_res_change = d

    @property
    def is_full(self):
        return len(self.passengers) >= self._capacity

    @property
    def capacity(self):
        return self._capacity

    @property
    def is_empty(self):
        return not bool(self.passengers)

    @property
    def id(self):
        return self._global_id

    @property
    def type(self):
        return self.__class__.__name__

    @property
    def current_link(self):
        return self._current_link

    @property
    def current_node(self):
        return self._current_node

    @property
    def remaining_link_length(self):
        return self._remaining_link_length

    @property
    def position(self):
        return self._position

    @property
    def activity_type(self) -> ActivityType:
        return self.activity.activity_type if self.activity is not None else None

    @property
    def is_moving(self) -> bool:
        return self.activity.is_moving if self.activity is not None else False

    @property
    def dt_move(self) -> Dt:
        return self._dt_move

    @dt_move.setter
    def dt_move(self, dt):
        self._dt_move = dt

    @property
    def achieved_path(self):
        return self._achieved_path

    def update_achieved_path(self):
        if len(self.achieved_path) == 0 or self.current_node != self.achieved_path[-1]:
            self._achieved_path.append(self.current_node)
            self._achieved_path_since_last_notify.append(self.current_node)

    def flush_achieved_path_since_last_notify(self):
        self._achieved_path_since_last_notify = []

    def add_activities(self, activities:List[VehicleActivity]):
        for a in activities:
            self.activities.append(a)

    def next_activity(self, tcurrent: Time):
        if self.activity is not None:
            self.activity.done(self, tcurrent)

        try:
            activity = self.activities.popleft()
        except IndexError:
            activity = self.default_activity()

        self.activity = activity
        self.activity.start(self)
        if activity.activity_type is not ActivityType.STOP:
            if activity.path:
                self._current_link, self._remaining_link_length = next(activity.iter_path)
                assert self._current_node == self._current_link[0], f"Veh {self.id} current node {self._current_node} is not equal to the next upstream link {self._current_link[0]}"
            else:
                activity.is_done = True

    def override_current_activity(self):
        next_activity = self.activities.popleft()
        last_activity = self.activity
        self.activity = next_activity
        self.activity.start(self)

        if last_activity.activity_type is ActivityType.STOP:
            if next_activity.path:
                self._current_link, self._remaining_link_length = next(next_activity.iter_path)
                assert self._current_node == self._current_link[0]
            else:
                next_activity.is_done = True

    def iter_activities(self):
        yield self.activity
        for act in self.activities:
            yield act

    def set_path(self, path: List[Tuple[Tuple[str, str], float]]):
        self._iter_path = iter(path)
        self._current_link, self._remaining_link_length = next(self._iter_path)

    def update_distance(self, dist: float):
        self._distance += dist
        for user in self.passengers.values():
            user.update_distance(dist)

    def set_position(self, position: np.ndarray):
        self._position = position

    def drop_user(self, tcurrent:Time, user:'User', drop_pos:np.ndarray):
        log.info(f"{user} is dropped at {self._current_link[0]}")
        user.remaining_link_length = 0
        upath = user.path.nodes
        unode = self._current_link[0]
        next_node_ind = user.get_node_index_in_path(unode)+1
        user.set_position((unode, upath[next_node_ind]), unode, 0, drop_pos, tcurrent)
        user.vehicle = None
        user.notify(tcurrent)

        del self.passengers[user.id]

    def drop_all_passengers(self, tcurrent:Time):
        for _, user in self.passengers.values():
            log.info(f"{user} is dropped at {self._current_link[1]}")
            unode = self._current_link[1]
            user.current_node = unode
            user.remaining_link_length = 0
            user.position = self._position
            user.notify(tcurrent)
            user.vehicle = None

        self.passengers = dict()

    def start_user_trip(self, userid, take_node):
        log.info(f'Passenger {userid} has been taken by {self} at {take_node}')
        take_time, user = self._next_passenger.pop(userid)
        user.vehicle = self.id
        self.passengers[userid] = (take_time, user)

    def default_activity(self):
        return VehicleActivityStop(node=self._current_node,
                                   path=[],
                                   is_done=False)

    def notify_passengers(self, tcurrent: Time):
        for user in self.passengers.values():
            user.notify(tcurrent)

    def path_to_nodes(self, path):
        """Method that converts a VehicleActivity path into a list of nodes.

        Args:
            -path: path to convert

        Returns:
            -path_nodes: the converted path
        """
        if len(path) > 0:
            path_nodes = [l[0][0] for l in path] + [path[-1][0][1]]
        else:
            path_nodes = [self._current_node]
        return path_nodes

    @classmethod
    def reset_counter(cls):
        cls._counter = 0


class Car(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool,
                 activities: Optional[VehicleActivity] = None):
        super(Car, self).__init__(node, capacity, mobility_service, is_personal, activities)
        self._last_dropped_off_user = None

    @property
    def last_dropped_off_user(self):
        return self._last_dropped_off_user

    @last_dropped_off_user.setter
    def last_dropped_off_user(self, user):
        self._last_dropped_off_user = user

class Bus(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: Optional[VehicleActivity] = None):
        super(Bus, self).__init__(node, capacity, mobility_service, is_personal, activities)


class Tram(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: Optional[VehicleActivity] = None):
        super(Tram, self).__init__(node, capacity, mobility_service, is_personal, activities)


class Metro(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: Optional[VehicleActivity] = None):
        super(Metro, self).__init__(node, capacity, mobility_service, is_personal, activities)


class Bike(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool,
                 activities: Optional[VehicleActivity] = None):
        super(Bike, self).__init__(node, capacity, mobility_service, is_personal, activities)

class Train(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: Optional[VehicleActivity] = None):
        super(Train, self).__init__(node, capacity, mobility_service, is_personal, activities)


