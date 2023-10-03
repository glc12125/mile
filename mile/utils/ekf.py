import numpy as np
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import time
from scipy.stats import norm
from sympy import Symbol, symbols, Matrix, sin, cos
from sympy import init_printing
from sympy.utilities.codegen import codegen
init_printing(use_latex=True)


class EkfCtra(object):
    def __init__(self, carla_fps):
        self._numstates = 6
        # Sample Rate of the control signals is 10Hz
        self._dt = 1.0/float(carla_fps)
        vs, psis, dpsis, dts, xs, ys, lats, lons, axs = symbols(
            'v \psi \dot\psi T x y lat lon a')

        self._gs = Matrix([[xs + (1 / dpsis**2) * ((vs*dpsis + axs * dpsis * dts) * sin(psis + dpsis * dts) + axs * cos(psis + dpsis * dts) - vs * dpsis * sin(psis) - axs * cos(psis))],
                           [ys + (1 / dpsis**2) * ((-vs*dpsis - axs * dpsis * dts) * cos(psis + dpsis * dts) +
                                                   axs * sin(psis + dpsis * dts) + vs * dpsis * cos(psis) - axs * sin(psis))],
                           [psis+dpsis*dts],
                           [axs*dts + vs],
                           [dpsis],
                           [axs]])
        self._state = Matrix([xs, ys, psis, vs, dpsis, axs])
        self._P = np.diag([1000.0, 1000.0, 1000.0, 1000.0, 1000.0, 1000.0])
        print(self._P, self._P.shape)
        # assume 8.8m/s2 as maximum acceleration, forcing the vehicle
        self._sGPS = 0.5*8.8*self._dt**2
        self._sCourse = 0.1*self._dt  # assume 0.1rad/s as maximum turn rate for the vehicle
        # assume 8.8m/s2 as maximum acceleration, forcing the vehicle
        self._sVelocity = 8.8*self._dt
        # assume 1.0rad/s2 as the maximum turn rate acceleration for the vehicle
        self._sYaw = 1.0*self._dt
        self._sAccel = 0.5

        self._Q = np.diag([self._sGPS**2, self._sGPS**2, self._sCourse **
                          2, self._sVelocity**2, self._sYaw**2, self._sAccel**2])
        print(self._Q, self._Q.shape)
        self._hs = Matrix([[xs],
                           [ys],
                           [vs],
                           [dpsis],
                           [axs]])
        self._JHs = self._hs.jacobian(self._state)
        varGPS = 5.0  # Standard Deviation of GPS Measurement
        varspeed = 3.0  # Variance of the speed measurement
        varyaw = 0.1  # Variance of the yawrate measurement
        varacc = 1.0  # Variance of the longitudinal Acceleration
        self._R = np.diag(
            [varGPS**2, varGPS**2, varspeed**2, varyaw**2, varacc**2])

        print(self._R, self._R.shape)

        self._I = np.eye(self._numstates)
        print(self._I, self._I.shape)
        self._first_state_initialized = False

    def init_sate(self, x, y, heading, speed, yawrate, longitudinal_acceleration):
        # heading: A heading of 0° means the Car is traveling north bound
        #   and 90° means it is traveling east bound.
        #   In the Calculation following, East is Zero and North is 90°
        #   We need an offset. And it is in radian.
        # speed: The speed is measured in m/s.
        # yawrate: The yaw rate is given in rad/s
        # longitudinal_acceleration: The acceleration is given in m/s2
        self._x = np.matrix(
            [[x, y, heading, speed + 0.001, yawrate, longitudinal_acceleration]]).T
        print(self._x, self._x.shape)
        self._first_state_initialized = True

    def predict(self, yawrate):
        # Time Update (Prediction)
        # ========================
        # Project the state ahead
        # see "Dynamic Matrix"
        if np.abs(yawrate) < 0.0001:  # Driving straight
            self._x[4] = 0.0001
        self._x[0] = self._x[0] + (1 / self._x[4]**2) * ((self._x[3]*self._x[4] + self._x[5] * self._x[4] * self._dt) * np.sin(self._x[2] + self._x[4] * self._dt) +
                                                         self._x[5] * np.cos(self._x[2] + self._x[4] * self._dt) - self._x[3] * self._x[4] * np.sin(self._x[2]) - self._x[5] * np.cos(self._x[2]))
        self._x[1] = self._x[1] + (1 / self._x[4]**2) * ((-self._x[3]*self._x[4] - self._x[5] * self._x[4] * self._dt) * np.cos(self._x[2] + self._x[4] * self._dt) +
                                                         self._x[5] * np.sin(self._x[2] + self._x[4] * self._dt) + self._x[3] * self._x[4] * np.cos(self._x[2]) - self._x[5] * np.sin(self._x[2]))
        self._x[2] = (self._x[2] + self._x[4] * self._dt +
                      np.pi) % (2.0 * np.pi) - np.pi
        self._x[3] = self._x[3] + self._x[5] * self._dt
        self._x[4] = self._x[4]
        self._x[5] = self._x[5]

        # Calculate the Jacobian of the Dynamic Matrix A
        # see "Calculate the Jacobian of the Dynamic Matrix with respect to the state vector"
        a13 = ((-self._x[4]*self._x[3]*np.cos(self._x[2]) + self._x[5]*np.sin(self._x[2]) - self._x[5]*np.sin(self._dt*self._x[4] + self._x[2]) +
                (self._dt*self._x[4]*self._x[5] + self._x[4]*self._x[3])*np.cos(self._dt*self._x[4] + self._x[2]))/self._x[4]**2).item(0)

        a14 = ((-self._x[4]*np.sin(self._x[2]) + self._x[4] *
               np.sin(self._dt*self._x[4] + self._x[2]))/self._x[4]**2).item(0)

        a15 = ((-self._dt*self._x[5]*np.sin(self._dt*self._x[4] + self._x[2]) + self._dt*(self._dt*self._x[4]*self._x[5] + self._x[4]*self._x[3]) *
                np.cos(self._dt*self._x[4] + self._x[2]) - self._x[3]*np.sin(self._x[2]) + (self._dt*self._x[5] + self._x[3]) *
                np.sin(self._dt*self._x[4] + self._x[2]))/self._x[4]**2 - 2*(-self._x[4]*self._x[3]*np.sin(self._x[2]) - self._x[5] *
                                                                             np.cos(self._x[2]) + self._x[5]*np.cos(self._dt*self._x[4] + self._x[2]) + (self._dt*self._x[4]*self._x[5] + self._x[4]*self._x[3]) *
                                                                             np.sin(self._dt*self._x[4] + self._x[2]))/self._x[4]**3).item(0)

        a16 = ((self._dt*self._x[4]*np.sin(self._dt*self._x[4] + self._x[2]) - np.cos(
            self._x[2]) + np.cos(self._dt * self._x[4] + self._x[2]))/self._x[4]**2).item(0)

        a23 = ((-self._x[4] * self._x[3] * np.sin(self._x[2]) - self._x[5] * np.cos(self._x[2]) + self._x[5] * np.cos(self._dt * self._x[4] + self._x[2]) -
                (-self._dt * self._x[4]*self._x[5] - self._x[4] * self._x[3]) * np.sin(self._dt * self._x[4] + self._x[2])) / self._x[4]**2).item(0)
        a24 = ((self._x[4] * np.cos(self._x[2]) - self._x[4] *
               np.cos(self._dt*self._x[4] + self._x[2]))/self._x[4]**2).item(0)
        a25 = ((self._dt * self._x[5]*np.cos(self._dt*self._x[4] + self._x[2]) - self._dt * (-self._dt*self._x[4]*self._x[5] - self._x[4] * self._x[3]) *
                np.sin(self._dt * self._x[4] + self._x[2]) + self._x[3]*np.cos(self._x[2]) + (-self._dt*self._x[5] - self._x[3])*np.cos(self._dt*self._x[4] + self._x[2])) /
               self._x[4]**2 - 2*(self._x[4]*self._x[3]*np.cos(self._x[2]) - self._x[5] * np.sin(self._x[2]) + self._x[5] * np.sin(self._dt*self._x[4] + self._x[2]) +
                                  (-self._dt * self._x[4] * self._x[5] - self._x[4] * self._x[3])*np.cos(self._dt*self._x[4] + self._x[2]))/self._x[4]**3).item(0)
        a26 = ((-self._dt*self._x[4]*np.cos(self._dt*self._x[4] + self._x[2]) - np.sin(
            self._x[2]) + np.sin(self._dt*self._x[4] + self._x[2]))/self._x[4]**2).item(0)

        self._JA = np.matrix([[1.0, 0.0, a13, a14, a15, a16],
                              [0.0, 1.0, a23, a24, a25, a26],
                              [0.0, 0.0, 1.0, 0.0, self._dt, 0.0],
                              [0.0, 0.0, 0.0, 1.0, 0.0, self._dt],
                              [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                              [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]])
        # Project the error covariance ahead
        self._P = self._JA*self._P*self._JA.T + self._Q

        return self._x

    def update(self, x, y, heading, speed, yawrate, longitudinal_acceleration):

        if not self._first_state_initialized:
            self.init_sate(x, y, heading, speed, yawrate,
                           longitudinal_acceleration)
        # Measurement Update (Correction)
        # ===============================
        # Measurement Function
        hx = np.matrix([[float(self._x[0])],
                        [float(self._x[1])],
                        [float(self._x[3])],
                        [float(self._x[4])],
                        [float(self._x[5])]])

        JH = np.matrix([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0, 0.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]])

        self._S = JH*self._P*JH.T + self._R
        K = (self._P*JH.T) * np.linalg.inv(self._S)

        # Update the estimate via
        Z = np.array([x, y, speed, yawrate,
                      longitudinal_acceleration]).reshape(JH.shape[0], 1)
        y = Z - (hx)                         # Innovation or Residual
        self._x = self._x + (K*y)

        # Update the error covariance
        self._P = (self._I - (K*JH))*self._P
