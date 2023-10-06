"""Adapted from https://github.com/zhejz/carla-roach/ CC-BY-NC 4.0 license."""

import gym
import json
from pathlib import Path
import wandb
import hydra
from omegaconf import DictConfig, OmegaConf, open_dict
import logging
import os.path
import sys
from pprint import pprint
from time import time
import collections
import datetime
import re
import weakref
import carla
from carla import ColorConverter as cc
from agents.navigation.global_route_planner import GlobalRoutePlanner
import cv2
import matplotlib.pyplot as plt

import math
import threading
from queue import Queue
from queue import Empty

from gym.wrappers.monitoring.video_recorder import ImageEncoder
from stable_baselines3.common.vec_env.base_vec_env import tile_images

from carla_gym.utils import config_utils
from utils import server_utils
from mile.utils import carla_utils, ekf
from mile.agents.rl_birdview.utils.wandb_callback import WandbCallback
from mile.constants import CARLA_FPS

try:
    import pygame
    from pygame.locals import KMOD_SHIFT
    from pygame.locals import KMOD_CTRL
    from pygame.locals import K_ESCAPE
    from pygame.locals import K_q
    from pygame.locals import K_c
    from pygame.locals import K_n
    from pygame.locals import K_TAB
except ImportError:
    raise RuntimeError(
        'cannot import pygame, make sure pygame package is installed')

try:
    import numpy as np
except ImportError:
    raise RuntimeError(
        'cannot import numpy, make sure numpy package is installed')

log = logging.getLogger(__name__)

QUANTUM_RATIO = 1
# pygame related

# ==============================================================================
# -- Global functions ----------------------------------------------------------
# ==============================================================================


def find_weather_presets():
    """Method to find weather presets"""
    rgx = re.compile('.+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)')
    def name(x): return ' '.join(m.group(0) for m in rgx.finditer(x))
    presets = [x for x in dir(carla.WeatherParameters)
               if re.match('[A-Z].+', x)]
    return [(getattr(carla.WeatherParameters, x), name(x)) for x in presets]


def get_actor_display_name(actor, truncate=250):
    """Method to get actor display name"""
    name = ' '.join(actor.type_id.replace('_', '.').title().split('.')[1:])
    return (name[:truncate - 1] + u'\u2026') if len(name) > truncate else name

# ==============================================================================
# -- World ---------------------------------------------------------------
# ==============================================================================


class World(object):
    """ Class representing the surrounding environment """

    def __init__(self, carla_world, hud, args):
        """Constructor method"""
        self.world = carla_world

        try:
            self.map = self.world.get_map()
        except RuntimeError as error:
            print('RuntimeError: {}'.format(error))
            print('  The server could not send the OpenDRIVE (.xodr) file:')
            print(
                '  Make sure it exists, has the same name of your town, and is correct.')
            sys.exit(1)
        self.hud = hud
        self.player = None
        self.max_steering_angle = 70
        self.collision_sensor = None
        self.lane_invasion_sensor = None
        self.gnss_sensor = None
        self.camera_manager = None
        self._weather_presets = find_weather_presets()
        self._weather_index = 0
        self._actor_filter = args.filter
        self._gamma = args.gamma
        self._ekf_ctra = None
        self._show_way = args.show_way
        self.restart(args)
        self.world.on_tick(hud.on_world_tick)
        self.recording_enabled = False
        self.recording_start = 0
        self._hop_resolution = 2
        self._grp = None

        self._spectator = None
        # self._isDroneView = args.drone_view
        # self._isParasailView = args.parasail_view
        # if self._isDroneView or self._isParasailView:
        #    self._spectator = self.world.get_spectator()

    def restart(self, args):
        # This handy piece of code can be used to dump the blueprint library.
        #       print("------- Blueprint library begin -----")
        #       blueprints = [bp for bp in self.world.get_blueprint_library().filter('*')]
        #       for bp in blueprints:
        #          print(bp.id)
        #          for attr in bp:
        #              print('  - {}'.format(attr))
        #       print("------- Blueprint library end -----")
        """Restart the world"""
        # Keep same camera config if the camera manager exists.
        cam_index = self.camera_manager.index if self.camera_manager is not None else 0
        cam_pos_id = self.camera_manager.transform_index if self.camera_manager is not None else 0
        # Set the seed if requested by user
        # if args.seed is not None:
        #    random.seed(args.seed)

        # Get a random blueprint.
        # NOTE: Original code retrieved a random blueprint. However, here it
        # has been modified to fix the vehicle type, color, and starting point.
        # blueprint = random.choice(self.world.get_blueprint_library().filter(self._actor_filter))
        # blueprint = self.world.get_blueprint_library().filter("vehicle.lincoln.mkz2017")[0]
        # blueprint = self.world.get_blueprint_library().filter("vehicle.mustang.mustang")[0]
        # blueprint = self.world.get_blueprint_library().filter("vehicle.tesla.model3")[0]
        # blueprint = self.world.get_blueprint_library().filter("vehicle.audi.tt")[0]
        # blueprint = self.world.get_blueprint_library().filter(
        #    "vehicle.chevrolet.impala")[0]
        # blueprint.set_attribute('role_name', 'hero')
        # if blueprint.has_attribute('color'):
        #    color = random.choice(blueprint.get_attribute('color').recommended_values)
        #    blueprint.set_attribute('color', color)
        # Spawn the player.
        # print("Spawning the player")
        # if self.player is not None:
        #    spawn_point = self.player.get_transform()
        #    spawn_point.location.z += 2.0
        #    spawn_point.rotation.roll = 0.0
        #    spawn_point.rotation.pitch = 0.0
        #    self.destroy()
        #    self.player = self.world.try_spawn_actor(blueprint, spawn_point)

        # while self.player is None:
        #    if not self.map.get_spawn_points():
        #        print('There are no spawn points available in your map/town.')
        #        print('Please add some Vehicle Spawn Point to your UE4 scene.')
        #        sys.exit(1)
        #    spawn_points = self.map.get_spawn_points()
        #    # NOTE: Original code retrieved a random starting point. However,
        #    # here it has been modified to fix the vehicle starting point in
        #    # the simulation so as to make it repeatable. Also we do a similar
        #    # thing for vehicle destination (see johnS 4-28-21 comment below)
        #    # -- johnS 1-28-21
        #    # spawn_point = random.choice(spawn_points) if spawn_points else carla.Transform()
        #    spawn_point = spawn_points[3]
        #    self.player = self.world.try_spawn_actor(blueprint, spawn_point)

        for actor in self.world.get_actors().filter('vehicle.*'):
            print("actor attributes: {}".format(actor.attributes))
            if actor.attributes.get('role_name') == 'hero':
                self.player = actor
                print("Found player")
                self.max_steering_angle = carla_utils.get_vehicle_max_steering_angle(
                    self.player)
                print("max steering angle: {}".format(self.max_steering_angle))
                # physics_control = self.player.get_physics_control()
                # print("max steering angler for wheel 0: {}".format(
                #    physics_control.wheels[0].max_steer_angle))
                # if physics_control.wheels[0].max_steer_angle > 0:
                #    self.max_steering_angle = min(
                #        self.max_steering_angle, physics_control.wheels[0].max_steer_angle)
                # print("max steering angler for wheel 1: {}".format(
                #    physics_control.wheels[1].max_steer_angle))
                # if physics_control.wheels[1].max_steer_angle > 0:
                #    self.max_steering_angle = min(
                #        self.max_steering_angle, physics_control.wheels[1].max_steer_angle)
                # print("max steering angler for wheel 2: {}".format(
                #    physics_control.wheels[2].max_steer_angle))
                # print("max steering angler for wheel 3: {}".format(
                #    physics_control.wheels[3].max_steer_angle))
                break
        if self.player is None:
            print("Cannot find player, will exit")
            exit(-1)
        # Set up the sensors.
        self.collision_sensor = CollisionSensor(self.player, self.hud)
        self.lane_invasion_sensor = LaneInvasionSensor(self.player, self.hud)
        # self.gnss_sensor = GnssSensor(self.player)
        self.camera_manager = CameraManager(
            self.player, self.hud, self._gamma, args)
        self.camera_manager.transform_index = cam_pos_id
        self.camera_manager.set_sensor(cam_index, notify=False)
        actor_type = get_actor_display_name(self.player)
        self.hud.notification(actor_type)

        if args.use_ekf:
            self._ekf_ctra = ekf.EkfCtra(CARLA_FPS)
        # if args.drone_view or args.parasail_view:
        #    self._spectator = self.world.get_spectator()

    def next_weather(self, reverse=False):
        """Get next weather setting"""
        self._weather_index += -1 if reverse else 1
        self._weather_index %= len(self._weather_presets)
        preset = self._weather_presets[self._weather_index]
        self.hud.notification('Weather: %s' % preset[1])
        self.player.get_world().set_weather(preset[0])

    def tick(self, clock, ego_loc_vector, ego_loc_vector_next, controls):
        """Method for every tick"""
        # PAVE360: Added world tick for synchronous mode
        # self.world.tick()
        self.hud.tick(self, clock)

        if self._spectator is not None:
            ego_trans = self.player.get_transform()
            if self._isDroneView:
                self._spectator.set_transform(
                    carla.Transform(ego_trans.location + carla.Location(z=50),
                                    carla.Rotation(pitch=-90)))
            elif self._isParasailView:
                rot = ego_trans.rotation
                deltax = -math.cos(math.radians(rot.yaw))*20
                deltay = -math.sin(math.radians(rot.yaw))*20
                self._spectator.set_transform(
                    carla.Transform(
                        ego_trans.location + carla.Location(
                            x=deltax, y=deltay, z=20),
                        carla.Rotation(
                            pitch=rot.pitch-20, yaw=rot.yaw, roll=rot.roll)))
        if self._show_way and len(ego_loc_vector) > 0:
            ego_trans = self.player.get_transform()
            start_waypoint = self.map.get_waypoint(ego_trans.location)
            end_waypoint = self.map.get_waypoint(carla.Location(
                float(ego_loc_vector[0]) + ego_trans.location.x, float(ego_loc_vector[1]) + ego_trans.location.y, ego_trans.location.z))
            print('Ego position:% 20s' % ('(% 5.1f, % 5.1f)' %
                                          (ego_trans.location.x, ego_trans.location.y)))
            print('Target position:% 20s' % ('(% 5.1f, % 5.1f)' %
                                             (end_waypoint.transform.location.x, end_waypoint.transform.location.y)))
            route_trace = self._trace_route(start_waypoint, end_waypoint)
            print("\n")
            self._draw_waypoints(route_trace)
            print("\n")
        if self._ekf_ctra and controls:
            # x, y, heading, speed, yawrate, longitudinal_acceleration
            ego_trans = self.player.get_transform()
            x = ego_trans.location.x
            y = ego_trans.location.y
            heading = -ego_trans.rotation.yaw + 90.0
            # heading = -ego_trans.rotation.yaw
            print("carla yaw: {}, heading: {}".format(
                ego_trans.rotation.yaw, heading))
            speed = carla_utils.get_vehicle_lon_speed(self.player)
            yawrate = controls.steer * self.max_steering_angle
            print("speed: {}".format(speed))
            print("yawrate: {}".format(yawrate))
            longitudinal_acceleration = carla_utils.get_vehicle_max_acceleration(self.player) * \
                controls.throttle
            self._ekf_ctra.update(x, y, heading/180.0*np.pi,
                                  speed[0], yawrate, longitudinal_acceleration)
            print('Ego position:% 20s' % ('(% 5.1f, % 5.1f)' %
                                          (ego_trans.location.x, ego_trans.location.y)))
            for i in range(12):
                next_position = self._ekf_ctra.predict(yawrate)
                print('EKF: next position:% 20s' % ('(% 5.1f, % 5.1f), % 5.3f seconds ahead' %
                                                    (next_position.item(0, 0), next_position.item(1, 0), (i + 1) * 1.0/float(CARLA_FPS))))
                # start_waypoint = self.map.get_waypoint(ego_trans.location)
                end_waypoint = self.map.get_waypoint(carla.Location(
                    float(next_position.item(0, 0)), next_position.item(1, 0), ego_trans.location.z))
                # route_trace = self._trace_route(start_waypoint, end_waypoint)
                self._draw_waypoints([[end_waypoint, None]], red=0,
                                     green=255, blue=0, life=-1)
            print("\n")

    def render(self, display):
        """Render world"""
        self.camera_manager.render(display)
        self.hud.render(display)

    def _draw_waypoints(self, route, red=255, green=0, blue=0, life=360):
        lastx = 0
        lasty = 0
        lastz = 0
        for (waypoint, _) in route:
            # Avoid drawing duplicates ...
            if waypoint.transform.location.x != lastx or waypoint.transform.location.y != lasty or waypoint.transform.location.z != lastz:
                self.world.debug.draw_point(
                    carla.Location(waypoint.transform.location.x,
                                   waypoint.transform.location.y, 1.0),
                    0.04, carla.Color(r=red, g=green, b=blue), life_time=life)
            # print("waypoint x: {}, y: {}, z: {}".format(waypoint.transform.location.x,
            #      waypoint.transform.location.y, waypoint.transform.location.z))
            lastx = waypoint.transform.location.x
            lasty = waypoint.transform.location.y
            lastz = waypoint.transform.location.z

    def _trace_route(self, start_waypoint, end_waypoint):
        """
        This method sets up a global router and returns the optimal route
        from start_waypoint to end_waypoint
        """

        # Setting up global router
        if self._grp is None:
            # carla 0.9.11 API uses DAO, it is deprecated in 0.9.12
            grp = GlobalRoutePlanner(self.map, self._hop_resolution)
            grp.setup()
            self._grp = grp

        # Obtain route plan
        route = self._grp.trace_route(
            start_waypoint.transform.location,
            end_waypoint.transform.location)

        return route

    def destroy_sensors(self):
        """Destroy sensors"""
        self.camera_manager.sensor.destroy()
        self.camera_manager.sensor = None
        self.camera_manager.index = None

    def destroy(self):
        """Destroys all actors"""
        actors = [
            self.camera_manager.sensor,
            self.collision_sensor.sensor,
            self.lane_invasion_sensor.sensor,
            # self.gnss_sensor.sensor,
            self.player]
        for actor in actors:
            if actor is not None:
                actor.destroy()

        # Begin: PAVE360 integration mods: Disable sync mode on exit...
        settings = self.world.get_settings()
        settings.synchronous_mode = False
        self.world.apply_settings(settings)
        # ... End: PAVE360 integration mods


# ==============================================================================
# -- KeyboardControl -----------------------------------------------------------
# ==============================================================================


class KeyboardControl(object):
    def __init__(self, world):
        world.hud.notification("Press 'H' or '?' for help.", seconds=4.0)

    def parse_events(self, world):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return True
            if event.type == pygame.KEYUP:
                if self._is_quit_shortcut(event.key):
                    return True
                # elif event.key == K_c:
                #    world.next_weather()
                # elif event.key == K_c and pygame.key.get_mods() & KMOD_SHIFT:
                #    world.next_weather(reverse=True)
                elif event.key == K_n:
                    world.camera_manager.next_sensor()
                elif event.key == K_TAB:
                    world.camera_manager.toggle_camera()

    @staticmethod
    def _is_quit_shortcut(key):
        """Shortcut for quitting"""
        return (key == K_ESCAPE) or (key == K_q and pygame.key.get_mods() & KMOD_CTRL)


# ==============================================================================
# -- HUD -----------------------------------------------------------------------
# ==============================================================================


class HUD(object):
    """Class for HUD text"""

    def __init__(self, width, height):
        """Constructor method"""
        self.dim = (width, height)
        font = pygame.font.Font(pygame.font.get_default_font(), 20)
        font_name = 'courier' if os.name == 'nt' else 'mono'
        fonts = [x for x in pygame.font.get_fonts() if font_name in x]
        default_font = 'ubuntumono'
        mono = default_font if default_font in fonts else fonts[0]
        mono = pygame.font.match_font(mono)
        self._font_mono = pygame.font.Font(mono, 12 if os.name == 'nt' else 14)
        self._notifications = FadingText(font, (width, 40), (0, height - 40))
        self.help = HelpText(pygame.font.Font(mono, 24), width, height)
        self.server_fps = 0
        self.frame = 0
        self.simulation_time = 0
        self.simulated_time_in_ns = 0
        self._show_info = True
        self._info_text = []
        self._server_clock = pygame.time.Clock()

    def on_world_tick(self, timestamp):
        """Gets informations from the world at every tick"""
        self._server_clock.tick()
        self.server_fps = self._server_clock.get_fps()
        self.frame = timestamp.frame_count
        self.simulation_time = timestamp.elapsed_seconds

    def tick(self, world, clock):
        """HUD method for every tick"""
        self._notifications.tick(world, clock)
        if not self._show_info:
            return
        transform = world.player.get_transform()
        vel = world.player.get_velocity()
        control = world.player.get_control()
        heading = 'N' if abs(transform.rotation.yaw) < 89.5 else ''
        heading += 'S' if abs(transform.rotation.yaw) > 90.5 else ''
        heading += 'E' if 179.5 > transform.rotation.yaw > 0.5 else ''
        heading += 'W' if -0.5 > transform.rotation.yaw > -179.5 else ''
        colhist = world.collision_sensor.get_collision_history()
        collision = [colhist[x + self.frame - 200] for x in range(0, 200)]
        max_col = max(1.0, max(collision))
        collision = [x / max_col for x in collision]
        vehicles = world.world.get_actors().filter('vehicle.*')

        self._info_text = [
            'Server:  % 16.0f FPS' % self.server_fps,
            'Client:  % 16.0f FPS' % clock.get_fps(),
            '',
            'Vehicle: % 20s' % get_actor_display_name(
                world.player, truncate=20),
            'Map:     % 20s' % world.map.name,
            'Simulation time: % 12s' % datetime.timedelta(
                seconds=int(self.simulation_time)),
            'Simulated time: % 12f' % (
                self.simulated_time_in_ns * QUANTUM_RATIO / 1e9),
            '',
            'Speed:   % 15.0f km/h' % (3.6 *
                                       math.sqrt(vel.x**2 + vel.y**2 + vel.z**2)),
            u'Heading:% 16.0f\N{DEGREE SIGN} % 2s' % (
                transform.rotation.yaw, heading),
            'Location:% 20s' % ('(% 5.1f, % 5.1f)' %
                                (transform.location.x, transform.location.y)),
            #            'GNSS:% 24s' % ('(% 2.6f, % 3.6f)' %
            #                            (world.gnss_sensor.lat, world.gnss_sensor.lon)),
            'Height:  % 18.0f m' % transform.location.z,
            '']
        if isinstance(control, carla.VehicleControl):
            self._info_text += [
                ('Throttle:', control.throttle, 0.0, 1.0),
                ('Steer:', control.steer, -1.0, 1.0),
                ('Brake:', control.brake, 0.0, 1.0),
                ('Reverse:', control.reverse),
                ('Hand brake:', control.hand_brake),
                ('Manual:', control.manual_gear_shift),
                'Gear:        %s' % {-1: 'R', 0: 'N'}.get(control.gear, control.gear)]
        elif isinstance(control, carla.WalkerControl):
            self._info_text += [
                ('Speed:', control.speed, 0.0, 5.556),
                ('Jump:', control.jump)]
        self._info_text += [
            '',
            'Collision:',
            collision,
            '',
            'Number of vehicles: % 8d' % len(vehicles)]

        if len(vehicles) > 1:
            self._info_text += ['Nearby vehicles:']

        def dist(l):
            return math.sqrt((l.x - transform.location.x)**2 + (l.y - transform.location.y)
                             ** 2 + (l.z - transform.location.z)**2)
        vehicles = [(dist(x.get_location()), x)
                    for x in vehicles if x.id != world.player.id]

        for dist, vehicle in sorted(vehicles):
            if dist > 200.0:
                break
            vehicle_type = get_actor_display_name(vehicle, truncate=22)
            self._info_text.append('% 4dm %s' % (dist, vehicle_type))

    def toggle_info(self):
        """Toggle info on or off"""
        self._show_info = not self._show_info

    def notification(self, text, seconds=2.0):
        """Notification text"""
        self._notifications.set_text(text, seconds=seconds)

    def error(self, text):
        """Error text"""
        self._notifications.set_text('Error: %s' % text, (255, 0, 0))

    def render(self, display):
        """Render for HUD class"""
        if self._show_info:
            info_surface = pygame.Surface((220, self.dim[1]))
            info_surface.set_alpha(100)
            display.blit(info_surface, (0, 0))
            v_offset = 4
            bar_h_offset = 100
            bar_width = 106
            for item in self._info_text:
                if v_offset + 18 > self.dim[1]:
                    break
                if isinstance(item, list):
                    if len(item) > 1:
                        points = [(x + 8, v_offset + 8 + (1 - y) * 30)
                                  for x, y in enumerate(item)]
                        pygame.draw.lines(
                            display, (255, 136, 0), False, points, 2)
                    item = None
                    v_offset += 18
                elif isinstance(item, tuple):
                    if isinstance(item[1], bool):
                        rect = pygame.Rect(
                            (bar_h_offset, v_offset + 8), (6, 6))
                        pygame.draw.rect(display, (255, 255, 255),
                                         rect, 0 if item[1] else 1)
                    else:
                        rect_border = pygame.Rect(
                            (bar_h_offset, v_offset + 8), (bar_width, 6))
                        pygame.draw.rect(
                            display, (255, 255, 255), rect_border, 1)
                        fig = (item[1] - item[2]) / (item[3] - item[2])
                        if item[2] < 0.0:
                            rect = pygame.Rect(
                                (bar_h_offset + fig * (bar_width - 6), v_offset + 8), (6, 6))
                        else:
                            rect = pygame.Rect(
                                (bar_h_offset, v_offset + 8), (fig * bar_width, 6))
                        pygame.draw.rect(display, (255, 255, 255), rect)
                    item = item[0]
                if item:  # At this point has to be a str.
                    surface = self._font_mono.render(
                        item, True, (255, 255, 255))
                    display.blit(surface, (8, v_offset))
                v_offset += 18
        self._notifications.render(display)
        self.help.render(display)

# ==============================================================================
# -- FadingText ----------------------------------------------------------------
# ==============================================================================


class FadingText(object):
    """ Class for fading text """

    def __init__(self, font, dim, pos):
        """Constructor method"""
        self.font = font
        self.dim = dim
        self.pos = pos
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)

    def set_text(self, text, color=(255, 255, 255), seconds=2.0):
        """Set fading text"""
        text_texture = self.font.render(text, True, color)
        self.surface = pygame.Surface(self.dim)
        self.seconds_left = seconds
        self.surface.fill((0, 0, 0, 0))
        self.surface.blit(text_texture, (10, 11))

    def tick(self, _, clock):
        """Fading text method for every tick"""
        delta_seconds = 1e-3 * clock.get_time()
        self.seconds_left = max(0.0, self.seconds_left - delta_seconds)
        self.surface.set_alpha(500.0 * self.seconds_left)

    def render(self, display):
        """Render fading text method"""
        display.blit(self.surface, self.pos)

# ==============================================================================
# -- HelpText ------------------------------------------------------------------
# ==============================================================================


class HelpText(object):
    """ Helper class for text render"""

    def __init__(self, font, width, height):
        """Constructor method"""
        lines = __doc__.split('\n')
        self.font = font
        self.dim = (680, len(lines) * 22 + 12)
        self.pos = (0.5 * width - 0.5 *
                    self.dim[0], 0.5 * height - 0.5 * self.dim[1])
        self.seconds_left = 0
        self.surface = pygame.Surface(self.dim)
        self.surface.fill((0, 0, 0, 0))
        for i, line in enumerate(lines):
            text_texture = self.font.render(line, True, (255, 255, 255))
            self.surface.blit(text_texture, (22, i * 22))
            self._render = False
        self.surface.set_alpha(220)

    def toggle(self):
        """Toggle on or off the render help"""
        self._render = not self._render

    def render(self, display):
        """Render help text method"""
        if self._render:
            display.blit(self.surface, self.pos)

# ==============================================================================
# -- CollisionSensor -----------------------------------------------------------
# ==============================================================================


class CollisionSensor(object):
    """ Class for collision sensors"""

    def __init__(self, parent_actor, hud):
        """Constructor method"""
        self.sensor = None
        self.history = []
        self._parent = parent_actor
        self.hud = hud
        world = self._parent.get_world()
        blueprint = world.get_blueprint_library().find('sensor.other.collision')
        self.sensor = world.spawn_actor(
            blueprint, carla.Transform(), attach_to=self._parent)
        # We need to pass the lambda a weak reference to
        # self to avoid circular reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(
            lambda event: CollisionSensor._on_collision(weak_self, event))

    def get_collision_history(self):
        """Gets the history of collisions"""
        history = collections.defaultdict(int)
        for frame, intensity in self.history:
            history[frame] += intensity
        return history

    @staticmethod
    def _on_collision(weak_self, event):
        """On collision method"""
        self = weak_self()
        if not self:
            return
        actor_type = get_actor_display_name(event.other_actor)
        self.hud.notification('Collision with %r' % actor_type)
        impulse = event.normal_impulse
        intensity = math.sqrt(impulse.x ** 2 + impulse.y ** 2 + impulse.z ** 2)
        self.history.append((event.frame, intensity))
        if len(self.history) > 4000:
            self.history.pop(0)

# ==============================================================================
# -- LaneInvasionSensor --------------------------------------------------------
# ==============================================================================


class LaneInvasionSensor(object):
    """Class for lane invasion sensors"""

    def __init__(self, parent_actor, hud):
        """Constructor method"""
        self.sensor = None
        self._parent = parent_actor
        self.hud = hud
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find('sensor.other.lane_invasion')
        self.sensor = world.spawn_actor(
            bp, carla.Transform(), attach_to=self._parent)
        # We need to pass the lambda a weak reference to self to avoid circular
        # reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(
            lambda event: LaneInvasionSensor._on_invasion(weak_self, event))

    @staticmethod
    def _on_invasion(weak_self, event):
        """On invasion method"""
        self = weak_self()
        if not self:
            return
        lane_types = set(x.type for x in event.crossed_lane_markings)
        text = ['%r' % str(x).split()[-1] for x in lane_types]
        self.hud.notification('Crossed line %s' % ' and '.join(text))

# ==============================================================================
# -- GnssSensor --------------------------------------------------------
# ==============================================================================


class GnssSensor(object):
    """ Class for GNSS sensors"""

    def __init__(self, parent_actor):
        """Constructor method"""
        self.sensor = None
        self._parent = parent_actor
        self.lat = 0.0
        self.lon = 0.0
        world = self._parent.get_world()
        blueprint = world.get_blueprint_library().find('sensor.other.gnss')
        self.sensor = world.spawn_actor(blueprint, carla.Transform(carla.Location(x=1.0, z=2.8)),
                                        attach_to=self._parent)
        # We need to pass the lambda a weak reference to
        # self to avoid circular reference.
        weak_self = weakref.ref(self)
        self.sensor.listen(
            lambda event: GnssSensor._on_gnss_event(weak_self, event))

    @staticmethod
    def _on_gnss_event(weak_self, event):
        """GNSS method"""
        self = weak_self()
        if not self:
            return
        self.lat = event.latitude
        self.lon = event.longitude


# ==============================================================================
# -- CameraManager -------------------------------------------------------------
# ==============================================================================


class CameraManager(object):
    """ Class for camera management"""

    def __init__(self, parent_actor, hud, gamma_correction, args):
        """Constructor method"""
        self.sensor = None
        self.surface = None
        self._parent = parent_actor
        self.hud = hud
        self.recording = False
        self.imageQueue = Queue()  # Create a queue for camera images
        self.lidarImageQueue = Queue()  # Create a queue for lidar images
        self.actors = []
        self.leftCamSensor = {
            'type': 'sensor.camera.rgb',
            'x': 2.1, 'y': -0.5, 'z': 1.0,
            'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0,
            'width': 480,
            'height': 240,
            'fov': 72,
            'id': 'rgb_front_left'
        }
        self.rightCamSensor = {
            'type': 'sensor.camera.rgb',
            'x': 2.1, 'y': 0.5, 'z': 1.0,
            'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0,
            'width': 480,
            'height': 240,
            'fov': 72,
            'id': 'rgb_front_right'
        }
        bound_y = 0.5 + self._parent.bounding_box.extent.y
        attachment = carla.AttachmentType

        # We need to pass the lambda a weak reference to
        # self to avoid circular reference.
        weak_self = weakref.ref(self)
        # self.addStereoSensor(
        #    self.leftCamSensor, lambda image: CameraManager._handleLeftCam(weak_self, image))
        # self.addStereoSensor(
        #    self.rightCamSensor, lambda image: CameraManager._handleRightCam(weak_self, image))

        self._camera_transforms = [
            (carla.Transform(
                carla.Location(x=-5.5, z=2.5), carla.Rotation(pitch=8.0)), attachment.SpringArm),
            (carla.Transform(
                carla.Location(x=1.6, z=1.7)), attachment.Rigid),
            (carla.Transform(
                carla.Location(x=5.5, y=1.5, z=1.5)), attachment.SpringArm),
            (carla.Transform(
                carla.Location(x=-8.0, z=6.0), carla.Rotation(pitch=6.0)), attachment.SpringArm),
            (carla.Transform(
                carla.Location(x=-1, y=-bound_y, z=0.5)), attachment.Rigid)]
        self.transform_index = 1
        self.sensors = [
            ['sensor.camera.rgb', cc.Raw, 'Camera RGB']]

        world = self._parent.get_world()
        bp_library = world.get_blueprint_library()
        for item in self.sensors:
            blp = bp_library.find(item[0])
            if item[0].startswith('sensor.camera'):
                blp.set_attribute('image_size_x', str(hud.dim[0]))
                blp.set_attribute('image_size_y', str(hud.dim[1]))
                if blp.has_attribute('gamma'):
                    blp.set_attribute('gamma', str(gamma_correction))
            elif item[0].startswith('sensor.lidar'):
                blp.set_attribute('range', '50')
            item.append(blp)
        self.index = None

    def toggle_camera(self):
        """Activate a camera"""
        self.transform_index = (self.transform_index +
                                1) % len(self._camera_transforms)
        self.set_sensor(self.index, notify=False, force_respawn=True)

    def set_sensor(self, index, notify=True, force_respawn=False):
        """Set a sensor"""
        index = index % len(self.sensors)
        needs_respawn = True if self.index is None else (
            force_respawn or (self.sensors[index][0] != self.sensors[self.index][0]))
        if needs_respawn:
            if self.sensor is not None:
                self.sensor.destroy()
                self.surface = None
            self.sensor = self._parent.get_world().spawn_actor(
                self.sensors[index][-1],
                self._camera_transforms[self.transform_index][0],
                attach_to=self._parent,
                attachment_type=self._camera_transforms[self.transform_index][1])

            # We need to pass the lambda a weak reference to
            # self to avoid circular reference.
            weak_self = weakref.ref(self)
            self.sensor.listen(
                lambda image: CameraManager._parse_image(weak_self, image))
        if notify:
            self.hud.notification(self.sensors[index][2])
        self.index = index

    def next_sensor(self):
        """Get the next sensor"""
        self.set_sensor(self.index + 1)

    def toggle_recording(self):
        """Toggle recording on or off"""
        self.recording = not self.recording
        self.hud.notification('Recording %s' %
                              ('On' if self.recording else 'Off'))

    def render(self, display):
        """Render method"""
        if self.surface is not None:
            display.blit(self.surface, (0, 0))

    # This gets called for each of the 2 stereo camera sensors to set them up
    # and attach them to the actor as well as bind them to listener callbacks
    # that get called on each update.
    def addStereoSensor(self, sensor, listener):
        type = sensor['type']
        world = self._parent.get_world()
        bp = world.get_blueprint_library().find(type)
        assert bp, f"no blueprint found for {sensor['type']}"
        bp.set_attribute('fov', str(sensor['fov']))
        bp.set_attribute('image_size_x', str(sensor['width']))
        bp.set_attribute('image_size_y', str(sensor['height']))
        # bp.set_attribute('gamma', str(sensor.get('gamma', 2.2)))
        pos = carla.Transform(
            carla.Location(x=sensor['x'], y=sensor['y'], z=sensor['z']),
            carla.Rotation(pitch=sensor['pitch'], roll=sensor['roll'], yaw=sensor['yaw']))
        attachment = carla.AttachmentType
        # attachment_type = attachment.SpringArm
        actor = world.spawn_actor(bp, pos, attach_to=self._parent)
        self.actors.append(actor)
        actor.listen(listener)

    @staticmethod
    def _parse_image(weak_self, image):
        self = weak_self()
        if not self:
            return
        if self.sensors[self.index][0].startswith('sensor.lidar'):
            points = np.frombuffer(image.raw_data, dtype=np.dtype('f4'))
            points = np.reshape(points, (int(points.shape[0] / 4), 4))
            lidar_data = np.array(points[:, :2])
            lidar_data *= min(self.hud.dim) / 100.0
            lidar_data += (0.5 * self.hud.dim[0], 0.5 * self.hud.dim[1])
            lidar_data = np.fabs(
                lidar_data)  # pylint: disable=assignment-from-no-return
            lidar_data = lidar_data.astype(np.int32)
            lidar_data = np.reshape(lidar_data, (-1, 2))
            lidar_img_size = (self.hud.dim[0], self.hud.dim[1], 3)
            lidar_img = np.zeros(lidar_img_size)
            lidar_img[tuple(lidar_data.T)] = (255, 255, 255)
            self.surface = pygame.surfarray.make_surface(lidar_img)
        else:
            image.convert(self.sensors[self.index][1])
            array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
            array = np.reshape(array, (image.height, image.width, 4))
            array = array[:, :, :3]
            array = array[:, :, ::-1]
            self.surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))

    @staticmethod
    def _handleLeftCam(weak_self, image):
        self = weak_self()
        if not self:
            return
        else:
            # print("@", paveCarlaGateway.getSimulationTimeInNs(), " ns leftCam")

            # Enqueue camera image so it can be synchronized with the next
            # tick. This technique was suggested in the carla-0.9.13
            # documentation on 'Synchrony and time-step'. The reason this is
            # important is that otherwise camera frames can "skip" into
            # next RTOS interval due to the async nature of camera sensor
            # interactions with the CarlaUE4 server. This behavior was being
            # observed frequently before this queueing fix. -- johnS 2-24-22
            self.imageQueue.put(image)

            # Here we (used to) broadcast the LEFT image frame to the TLM fabric
            # backplane for further processing. This is done over a separate
            # TLM channel that is basically set up as a TLM-2.0 base protocol
            # channel rather than an industry protocol flavored one.
            # We now use queueing as per comment above. -- johnS 2-24-22
            # paveCarlaGateway.sendVideoFrame(image.raw_data)

    @staticmethod
    def _handleRightCam(weak_self, image):
        self = weak_self()
        if not self:
            return
        else:
            # print("@", paveCarlaGateway.getSimulationTimeInNs(), " ns rightCam")

            # Enqueue camera image so it can be synchronized with the next
            # tick. (See note above about this in _handleLeftCam().
            # -- johnS 2-24-22
            self.imageQueue.put(image)

            # Here we (used to)broadcast the RIGHT image frame to the TLM fabric
            # backplane for further processing. This is done over a separate
            # TLM channel that is basically set up as a TLM-2.0 base protocol
            # channel rather than an industry protocol flavored one.
            # We now use queueing as per comment above. -- johnS 2-24-22
            # paveCarlaGateway.sendVideoFrame(image.raw_data)

    @staticmethod
    def _handleLidarSensor(weak_self, image):
        self = weak_self()
        if not self:
            return
        else:
            # print("@", paveCarlaGateway.getSimulationTimeInNs(), " ns DEBUG: lidarSens, frame#=", image.frame, "channels=", image.channels)
            self.lidarImageQueue.put(image)

# end of pygame related


def log_video_task(videos, info, actor_id, render_func):
    debug_image = render_func(
        info[actor_id]['reward_debug'], info[actor_id]['terminal_debug'])
    videos.append(debug_image)


def run_log_video_thread(videos, info, actor_id, render_func):
    t = threading.Thread(target=log_video_task, args=(
        videos, info, actor_id, render_func))
    print(f"Created Thread: {t}")
    t.start()
    return t


def run_single(run_name, env, agents_dict, agents_log_dir, log_video, cfg, max_step=None, show_debug=False):
    list_render = []
    ep_stat_dict = {}
    ep_event_dict = {}
    for actor_id, agent in agents_dict.items():
        log_dir = agents_log_dir / actor_id
        log_dir.mkdir(parents=True, exist_ok=True)
        agent.reset(log_dir / f'{run_name}.log')

    log.info(f'Start Benchmarking {run_name}.')
    obs = env.reset()
    timestamp = env.timestamp
    done = {'__all__': False}

    counter = 0
    warm_start = 25
    model_inference_avg_time = 0
    env_step_avg_time = 0
    render_stats_process_avg_time = 0
    end_to_end_start_time = 0
    end_to_end_end_time = 0
    end_to_end_avg_time = 0

    # pygame related
    client = env._client
    carla_world = env._world
    carla_map = env._map
    display = pygame.display.set_mode(
        (cfg.width, cfg.height), pygame.HWSURFACE | pygame.DOUBLEBUF)
    hud = HUD(cfg.width, cfg.height)
    world = World(carla_world, hud, cfg)
    controller = KeyboardControl(world)
    clock = pygame.time.Clock()
    # End of pygame related
    if show_debug:
        fig = plt.figure()
    while not done['__all__']:
        end_to_end_start_time = time()
        start_time = end_to_end_start_time
        control_dict = {}
        log_video_thread = None
        for actor_id, agent in agents_dict.items():
            control_dict[actor_id], gps_vector, gps_vector_next = agent.run_step(
                obs[actor_id], timestamp)

        end_time = time()
        execution_time = end_time - start_time
        if counter >= warm_start:
            print("--- Model inference time %s seconds ---" % (execution_time))
            model_inference_avg_time = (
                model_inference_avg_time * counter + execution_time) / (counter + 1)
            print("--- AVG Model inference time %s seconds ---" %
                  (model_inference_avg_time))

        start_time = time()
        world.tick(clock, gps_vector, gps_vector_next, control_dict[actor_id])
        world.render(display)
        pygame.display.flip()
        obs, reward, done, info = env.step(control_dict)
        end_time = time()
        execution_time = end_time - start_time
        if counter >= warm_start:
            print("--- Env step time %s seconds ---" % (execution_time))
            env_step_avg_time = (
                env_step_avg_time * counter + execution_time) / (counter + 1)
            print("--- AVG Env step time %s seconds ---" %
                  (env_step_avg_time))

        start_time = time()
        render_imgs = []
        for actor_id, agent in agents_dict.items():
            if log_video:
                # debug_image = agent.render(
                #    info[actor_id]['reward_debug'], info[actor_id]['terminal_debug'])
                # render_imgs.append(debug_image)
                log_video_thread = run_log_video_thread(
                    render_imgs, info, actor_id, agent.render)
            if show_debug:
                debug_image = agent.render(
                    info[actor_id]['reward_debug'], info[actor_id]['terminal_debug'])
                # cv2.imshow('BEV', debug_image)
                # cv2.waitKey(1)
                fig.figimage(debug_image)
                fig.canvas.draw()
                plt.pause(0.001)
            if done[actor_id] and (actor_id not in ep_stat_dict):
                ep_stat_dict[actor_id] = info[actor_id]['episode_stat']
                ep_event_dict[actor_id] = info[actor_id]['episode_event']

                # Add intersection-over-union metrics
                # custom_metrics = agent.compute_metrics()
                # ep_stat_dict[actor_id] = {
                #    **ep_stat_dict[actor_id], **custom_metrics}
        end_time = time()
        execution_time = end_time - start_time
        if counter >= warm_start:
            print("--- Render&Stats process time %s seconds ---" %
                  (execution_time))
            render_stats_process_avg_time = (
                render_stats_process_avg_time * counter + execution_time) / (counter + 1)
            print("--- AVG Render&Stats process time %s seconds ---" %
                  (render_stats_process_avg_time))

        if len(list_render) > 15000:
            del list_render[0]
        if log_video:
            log_video_thread.join()
            list_render.append(tile_images(render_imgs))

        timestamp = env.timestamp
        if max_step and timestamp['step'] > max_step:
            break

        end_to_end_end_time = time()
        execution_time = end_to_end_end_time - end_to_end_start_time
        if counter >= warm_start:
            print("--- End to end time %s seconds ---" % (execution_time))
            end_to_end_avg_time = (
                end_to_end_avg_time * counter + execution_time) / (counter + 1)
            print("--- AVG end to end time %s seconds ---" %
                  (end_to_end_avg_time))
        counter += 1
        if counter == warm_start:
            t0 = time()
    if world is not None:
        world.destroy()
    run_fps = (counter - warm_start) / (time() - t0)
    print(f'FPS: {run_fps:.1f}')

    return list_render, ep_stat_dict, ep_event_dict, timestamp


@hydra.main(config_path='config', config_name='pave')
def main(cfg: DictConfig):
    print("cfg:")
    pprint(cfg)
    log.setLevel(getattr(logging, cfg.log_level.upper()))
    with open_dict(cfg):
        cfg.width, cfg.height = [int(x) for x in cfg.res.split('x')]

    logging.info('listening to Carla server %s:%s', cfg.host, cfg.port)
    print(__doc__)

    try:
        game_loop(cfg)
    except KeyboardInterrupt:
        log.info('Cancelled by user. Bye!')


def game_loop(cfg):
    # initialize pave connections
    # ---------- Begin: PAVE360 integration mods: Enable sync mode ...
    '''
    paveCarlaGateway.connectToServer(args.comodel, args.domain, 50101)
    '''
    # Do an initial reset sync to insure that all conduit connections are
    # established from all clients before invoking async operations which could
    # potentially fail if propagated to clients that have not established
    # connections yet (TODO: Make it so TLM fabric infrastructure insures that
    # all conduit connections are established before any TLM traffic commences
    # - just as we do for client+server connections). -- johnS 12-31-20
    '''
    resetSuccess = paveCarlaGateway.waitForReset()
    if not resetSuccess:
        raise ConnectionError("Connection to FabricServer broken!")
    print("--- After reset: @", paveCarlaGateway.getSimulationTimeInNs(), " ns")
    '''
    # Above you see that we establish a connection to the to the TLM
    # FabricServer and waitForReset(), to get these wall clock time consuming
    # things done before we create the CarlaUE4 server interface and pygame
    # console below, and before we put the server connection into synchronous
    # mode because at this point it does not matter how much time these
    # operations consume - we don't start sync'ing with the CarlaUE4 server
    # until after these operations. The goal is to eliminate init-time wall
    # clock time race conditions. -- johnS 3-4-22
    # ... End: PAVE360 integration mods --------------

    # start carla servers
    server_manager = server_utils.CarlaServerManager(
        cfg.carla_sh_path, port=cfg.port)
    server_manager.start()  # it kills running carla servers first

    # single actor, place holder for multi actors
    agents_dict = {}
    obs_configs = {}
    reward_configs = {}
    terminal_configs = {}
    agent_names = []

    for ev_id, ev_cfg in cfg.actors.items():
        agent_names.append(ev_cfg.agent)
        pprint("ev_id: {}, ev_cfg: {}".format(ev_id, ev_cfg))
        cfg_agent = cfg.agent[ev_cfg.agent]
        OmegaConf.save(config=cfg_agent, f='config_agent.yaml')
        AgentClass = config_utils.load_entry_point(cfg_agent.entry_point)
        agents_dict[ev_id] = AgentClass('config_agent.yaml')
        obs_configs[ev_id] = agents_dict[ev_id].obs_configs

        # get obs_configs from agent
        reward_configs[ev_id] = OmegaConf.to_container(ev_cfg.reward)
        terminal_configs[ev_id] = OmegaConf.to_container(ev_cfg.terminal)

    # check h5 birdview maps have been generated
    config_utils.check_h5_maps(cfg.test_suites, obs_configs, cfg.carla_sh_path)

    env_idx = 0

    # This is used when resuming benchmarking to indicate that all scenarios were evaluated.
    if env_idx >= len(cfg.test_suites):
        log.info(f'Finished! env_idx: {env_idx}')
        server_manager.stop()
        return

    ckpt_task_idx = 0
    ep_stat_buffer = {}
    for actor_id in agents_dict.keys():
        ep_stat_buffer[actor_id] = []
    log.info(f'Start new env from task_idx {ckpt_task_idx}')

    ep_state_buffer_json = f'{hydra.utils.get_original_cwd()}/outputs/port_{cfg.port}_ep_stat_buffer_{env_idx}.json'
    # compose suite_name
    env_setup = OmegaConf.to_container(cfg.test_suites[env_idx])
    suite_name = '-'.join(agent_names) + '_' + env_setup['env_id']
    for k in sorted(env_setup['env_configs']):
        suite_name = suite_name + '_' + str(env_setup['env_configs'][k])

    log.info(
        f"Start Benchmarking! env_idx: {env_idx}, suite_name: {suite_name}")

    # make directories
    diags_dir = Path('diagnostics') / suite_name
    agents_log_dir = Path('agents_log') / suite_name
    video_dir = Path('videos') / suite_name
    diags_dir.mkdir(parents=True, exist_ok=True)
    agents_log_dir.mkdir(parents=True, exist_ok=True)
    video_dir.mkdir(parents=True, exist_ok=True)

    # make env
    print("env_setup['env_id']: {}, obs_configs: {}, reward_configs: {}, terminal_configs: {}".format(
        env_setup['env_id'], obs_configs, reward_configs, terminal_configs))
    env = gym.make(env_setup['env_id'], obs_configs=obs_configs, reward_configs=reward_configs,
                   terminal_configs=terminal_configs, host=cfg.host, port=cfg.port,
                   seed=cfg.seed, no_rendering=cfg.no_rendering, **env_setup['env_configs'])

    print("There are {} tasks in env {}".format(
        env.num_tasks, env_setup['env_id']))

    # pygame initialization
    pygame.init()
    pygame.font.init()

    try:
        if cfg.mode == 'all':
            # loop through each route
            for task_idx in range(ckpt_task_idx, env.num_tasks):
                env.set_task_idx(task_idx)
                run_name = f"{env.task['weather']}_{env.task['route_id']:02d}"

                list_render, ep_stat_dict, ep_event_dict, timestamp = run_single(
                    run_name, env, agents_dict, agents_log_dir, cfg.log_video, cfg)
                # log video
                if cfg.log_video:
                    video_path = (video_dir / f'{run_name}.mp4').as_posix()
                    encoder = ImageEncoder(
                        video_path, list_render[0].shape, 2*CARLA_FPS, 2*CARLA_FPS)
                    for im in list_render:
                        encoder.capture_frame(im)
                    encoder.close()
                    encoder = None

                # dump events
                diags_json_path = (
                    diags_dir / f'{task_idx:03}_{run_name}.json').as_posix()
                with open(diags_json_path, 'w') as fd:
                    json.dump(ep_event_dict, fd, indent=4, sort_keys=False)

                # save statistics
                for actor_id, ep_stat in ep_stat_dict.items():
                    ep_stat_buffer[actor_id].append(ep_stat)

                with open(ep_state_buffer_json, 'w') as fd:
                    json.dump(ep_stat_buffer, fd, indent=4, sort_keys=True)
                # clean up
                list_render.clear()
                ep_stat_dict = None
                ep_event_dict = None
        elif cfg.mode == 'single':
            task_idx = 0
            env.set_task_idx(task_idx)
            run_name = f"{env.task['weather']}_{env.task['route_id']:02d}"

            list_render, ep_stat_dict, ep_event_dict, timestamp = run_single(
                run_name, env, agents_dict, agents_log_dir, cfg.log_video, cfg, show_debug=cfg.show_debug)
            # log video
            if cfg.log_video:
                video_path = (video_dir / f'{run_name}.mp4').as_posix()
                encoder = ImageEncoder(
                    video_path, list_render[0].shape, 2*CARLA_FPS, 2*CARLA_FPS)
                for im in list_render:
                    encoder.capture_frame(im)
                encoder.close()
                encoder = None

            # dump events
            diags_json_path = (
                diags_dir / f'{task_idx:03}_{run_name}.json').as_posix()
            with open(diags_json_path, 'w') as fd:
                json.dump(ep_event_dict, fd, indent=4, sort_keys=False)

            # save statistics
            for actor_id, ep_stat in ep_stat_dict.items():
                ep_stat_buffer[actor_id].append(ep_stat)

            with open(ep_state_buffer_json, 'w') as fd:
                json.dump(ep_stat_buffer, fd, indent=4, sort_keys=True)
            # clean up
            list_render.clear()
            ep_stat_dict = None
            ep_event_dict = None
    finally:
        # close env
        env.close()
        env = None
        server_manager.stop()

        pygame.quit()
        # paveCarlaGateway.disconnectFromServer()
    # log after suite is completed
    table_data = []
    ep_stat_keys = None
    for actor_id, list_ep_stat in json.load(open(ep_state_buffer_json, 'r')).items():
        avg_ep_stat = WandbCallback.get_avg_ep_stat(list_ep_stat)
        data = [suite_name, actor_id, str(len(list_ep_stat))]
        if ep_stat_keys is None:
            ep_stat_keys = list(avg_ep_stat.keys())
        data += [f'{avg_ep_stat[k]:.4f}' for k in ep_stat_keys]
        table_data.append(data)

    log.info(
        f"Finished Benchmarking env_idx {env_idx}, suite_name: {suite_name}")
    if env_idx+1 == len(cfg.test_suites):
        log.info(f"Finished, {env_idx+1}/{len(cfg.test_suites)}")
        return
    else:
        log.info(f"Not finished, {env_idx+1}/{len(cfg.test_suites)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
    log.info("evaluate.py DONE!")
