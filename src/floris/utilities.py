# Copyright 2021 NREL

# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

# See https://floris.readthedocs.io for documentation

from typing import Any, Dict, List, Tuple, Union, Callable
from functools import partial, update_wrapper
from floris.type_dec import floris_array_converter, NDArrayFloat

from attrs import define, field
import attr
import numpy as np


@define
class Vec3:
    """
    Contains 3-component vector information. All arithmetic operators are
    set so that Vec3 objects can operate on and with each other directly.

    Args:
        components (list(numeric, numeric, numeric), numeric): All three vector
            components.
        string_format (str, optional): Format to use in the
            overloaded __str__ function. Defaults to None.
    """
    components: NDArrayFloat = field(converter=floris_array_converter)
    # NOTE: this does not convert elements to float if they are given as int. Is this ok?

    @components.validator
    def _check_components(self, attribute, value) -> None:        
        if np.ndim(value) > 1:
            raise ValueError(f"Vec3 must contain exactly 1 dimension, {np.ndim(value)} were given.")
        if np.size(value) != 3:
            raise ValueError(f"Vec3 must contain exactly 3 components, {np.size(value)} were given.")

    def __add__(self, arg):
        if type(arg) is Vec3:
            return Vec3(self.components + arg.components)
        elif type(arg) is int or type(arg) is float:
            return Vec3(self.components + arg)
        else:
            raise ValueError

    def __sub__(self, arg):
        if type(arg) is Vec3:
            return Vec3(self.components - arg.components)
        elif type(arg) is int or type(arg) is float:
            return Vec3(self.components - arg)
        else:
            raise ValueError

    def __mul__(self, arg):
        if type(arg) is Vec3:
            return Vec3(self.components * arg.components)
        elif type(arg) is int or type(arg) is float:
            return Vec3(self.components * arg)
        else:
            raise ValueError

    def __truediv__(self, arg):
        if type(arg) is Vec3:
            return Vec3(self.components / arg.components)
        elif type(arg) is int or type(arg) is float:
            return Vec3(self.components / arg)
        else:
            raise ValueError

    def __eq__(self, arg):
        return False not in np.isclose([self.x1, self.x2, self.x3], [arg.x1, arg.x2, arg.x3])

    def __hash__(self):
        return hash((self.x1, self.x2, self.x3))

    @property
    def x1(self):
        return self.components[0]

    @x1.setter
    def x1(self, value):
        self.components[0] = float(value)

    @property
    def x2(self):
        return self.components[1]

    @x2.setter
    def x2(self, value):
        self.components[1] = float(value)

    @property
    def x3(self):
        return self.components[2]

    @x3.setter
    def x3(self, value):
        self.components[2] = float(value)

    @property
    def elements(self) -> Tuple[float, float, float]:
        # TODO: replace references to elements with components
        # and remove this @property
        return self.components


def cosd(angle):
    """
    Cosine of an angle with the angle given in degrees.

    Args:
        angle (float): Angle in degrees.

    Returns:
        float
    """
    return np.cos(np.radians(angle))


def sind(angle):
    """
    Sine of an angle with the angle given in degrees.

    Args:
        angle (float): Angle in degrees.

    Returns:
        float
    """
    return np.sin(np.radians(angle))


def tand(angle):
    """
    Tangent of an angle with the angle given in degrees.

    Args:
        angle (float): Angle in degrees.

    Returns:
        float
    """
    return np.tan(np.radians(angle))


def wrap_180(x):
    """
    Shift the given values to within the range (-180, 180].

    Args:
        x (numeric or np.array): Scalar value or np.array of values to shift.

    Returns:
        np.array: Shifted values.
    """
    x = np.where(x <= -180.0, x + 360.0, x)
    x = np.where(x > 180.0, x - 360.0, x)
    return x


def wrap_360(x):
    """
    Shift the given values to within the range (0, 360].

    Args:
        x (numeric or np.array): Scalar value or np.array of values to shift.

    Returns:
        np.array: Shifted values.
    """
    x = np.where(x < 0.0, x + 360.0, x)
    x = np.where(x >= 360.0, x - 360.0, x)
    return x


def rotate_coordinates_rel_west(wind_directions, coordinates):
    # Calculate the difference in given wind direction from 270 / West
    wind_deviation_from_west = -1 * ((wind_directions - 270) % 360 + 360) % 360
    wind_deviation_from_west = np.reshape(wind_deviation_from_west, (len(wind_directions), 1, 1))

    # Construct the arrays storing the turbine locations
    x_coordinates, y_coordinates, z_coordinates = coordinates.T
    # x_coordinates = x_coordinates[None, None, :]
    # y_coordinates = y_coordinates[None, None, :]
    # z_coordinates = z_coordinates[None, None, :]

    # Find center of rotation - this is the center of box bounding all of the turbines
    x_center_of_rotation = (np.min(x_coordinates) + np.max(x_coordinates)) / 2
    y_center_of_rotation = (np.min(y_coordinates) + np.max(y_coordinates)) / 2

    # Rotate turbine coordinates about the center
    x_coord_offset = x_coordinates - x_center_of_rotation
    y_coord_offset = y_coordinates - y_center_of_rotation
    x_coord_rotated = (
        x_coord_offset * cosd(wind_deviation_from_west)
        - y_coord_offset * sind(wind_deviation_from_west)
        + x_center_of_rotation
    )
    y_coord_rotated = (
        x_coord_offset * sind(wind_deviation_from_west)
        + y_coord_offset * cosd(wind_deviation_from_west)
        + y_center_of_rotation
    )
    z_coord_rotated = np.ones_like(wind_deviation_from_west) * z_coordinates
    return x_coord_rotated, y_coord_rotated, z_coord_rotated


def pshape(array, label=""):
    print(label, np.shape(array))


def is_default(instance, attribute, value):
    if attribute.default != value:
        raise ValueError(f"{attribute.name} should never be set manually.")


def iter_validator(iter_type, item_types: Union[Any, Tuple[Any]]) -> Callable:
    """Helper function to generate iterable validators that will reduce the amount of
    boilerplate code.

    Parameters
    ----------
    iter_type : any iterable
        The type of iterable object that should be validated.
    item_types : Union[Any, Tuple[Any]]
        The type or types of acceptable item types.

    Returns
    -------
    Callable
        The attr.validators.deep_iterable iterable and instance validator.
    """
    validator = attr.validators.deep_iterable(
        member_validator=attr.validators.instance_of(item_types),
        iterable_validator=attr.validators.instance_of(iter_type),
    )
    return validator


def attrs_array_converter(data: list) -> np.ndarray:
    return np.array(data)


# Avoids constant redefinition of the same attr.ib properties for float model attributes
float_attrib = partial(
    attr.ib,
    converter=float,
    on_setattr=(attr.setters.convert, attr.setters.validate),  # type: ignore
    kw_only=True,
)
update_wrapper(float_attrib, attr.ib)

bool_attrib = partial(
    attr.ib,
    converter=bool,
    on_setattr=(attr.setters.convert, attr.setters.validate),  # type: ignore
    kw_only=True,
)
update_wrapper(bool_attrib, attr.ib)

# Avoids constant redefinition of the same attr.ib properties for int model attributes
int_attrib = partial(
    attr.ib,
    converter=int,
    on_setattr=(attr.setters.convert, attr.setters.validate),  # type: ignore
    kw_only=True,
)
update_wrapper(int_attrib, attr.ib)


model_attrib = partial(attr.ib, on_setattr=attr.setters.frozen, validator=is_default)  # type: ignore
update_wrapper(model_attrib, attr.ib)
