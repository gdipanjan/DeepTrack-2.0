'''Implementations of Feature the model scattering objects.

Provides some basic implementations of scattering objects 
that are frequently used.

Classes
--------
Scatterer
    Abstract base class for scatterers
PointParticle
    Generates point particles
Ellipse
    Generetes 2-d elliptical particles
Sphere
    Generates 3-d spheres
Ellipsoid
    Generates 3-d ellipsoids
'''

import numpy as np

from deeptrack.features import Feature, MERGE_STRATEGY_APPEND
from deeptrack.image import Image



class Scatterer(Feature):
    '''Base abstract class for scatterers.

    A scatterer is defined by a 3-dimensional volume of voxels. 
    To each voxel corresponds an occupancy factor, i.e., how much
    of that voxel does the scatterer occupy. However, this number is not
    necessarily limited to the [0, 1] range. It can be any number, and its
    interpretation is left to the optical device that images the scatterer.

    This abstract class implements the `_process_properties` method to convert
    the position to voxel units, as well as the `_process_and_get` method to 
    upsample the calculation and crop empty slices.

    Parameters
    ----------
    position : array_like of length 2 or 3
        The position of the  particle. Third index is optional, 
        and represents the position in the direction normal to the
        camera plane.
    z : float
        The position in the direction normal to the
        camera plane. Used if `position` is of length 2.
    value : float
        A default value of the characteristic of the particle. Used by
        optics unless a more direct property is set (eg. `refractive_index`
        for `Brightfield` and `intensity` for `Fluorescence`).
    position_unit : "meter" or "pixel"
        The unit of the provided position property.

    Other Parameters
    ----------------
    upsample_axes : tuple of ints
        Sets the axes along which the calculation is upsampled (default is None,
        which implies all axes are upsampled).
    crop_zeros : bool
        Whether to remove slices in which all elements are zero.
    '''

    __list_merge_strategy__ = MERGE_STRATEGY_APPEND
    __distributed__ = False


    def __init__(self,
                 position,
                 z=0.0,
                 value=1.0,
                 position_unit="meter",
                 upsample=1,
                 **kwargs):
        super().__init__(position=position,
                         z=z,
                         value=value,
                         position_unit=position_unit,
                         upsample=upsample,
                         **kwargs)


    def _process_properties(self, properties: dict) -> dict:
        # Rescales the position property

        if "position" in properties:
            if properties["position_unit"] == "meter":
                properties["position"] = np.array(properties["position"]) / np.array(properties["voxel_size"])[:len(properties["position"])]
        return properties


    def _process_and_get(self,
                         *args,
                         voxel_size,
                         upsample,
                         upsample_axes=None,
                         crop_empty=True,
                         **kwargs):
        # Post processes the created object to handle upsampling,
        # as well as cropping empty slices.

        # Calculates upsampled voxel_size
        if upsample_axes is None:
                upsample_axes = range(3)

        voxel_size = np.array(voxel_size)
        for axis in upsample_axes:
            voxel_size[axis] /= upsample

        # calls parent _process_and_get
        new_image = super()._process_and_get(*args, voxel_size=voxel_size, upsample=upsample, **kwargs)
        new_image = new_image[0]

        # Downsamples the image along the axes it was upsampled
        if upsample != 1 and upsample_axes:
            
            # Pad image to ensure it is divisible by upsample
            increase = np.array(new_image.shape)
            for axis in upsample_axes:
                increase[axis] = upsample - (new_image.shape[axis] % upsample)
            pad_width = [(0, inc) for inc in increase]
            new_image = np.pad(new_image, pad_width, mode='constant')

            # Finds reshape size for downsampling
            new_shape = []
            for axis in range(new_image.ndim):
                if axis in upsample_axes:
                    new_shape += [new_image.shape[axis] // upsample, upsample]
                else:
                    new_shape += [new_image.shape[axis]]

            # Downsamples
            new_image = np.reshape(new_image, new_shape).mean(axis=tuple(np.array(upsample_axes, dtype=np.int32) * 2 + 1))
            
        # Crops empty slices
        if crop_empty:
            new_image = new_image[~np.all(new_image == 0, axis=(1, 2))]
            new_image = new_image[:, ~np.all(new_image == 0, axis=(0, 2))]
            new_image = new_image[:, :, ~np.all(new_image == 0, axis=(0, 1))]

        return [Image(new_image)]



class PointParticle(Scatterer):
    '''Generates a point particle

    A point particle is approximated by the size of a pixel. For subpixel
    positioning, the position is interpolated linearly.

    Parameters
    ----------
    position : array_like of length 2 or 3
        The position of the  particle. Third index is optional, 
        and represents the position in the direction normal to the
        camera plane.
    z : float
        The position in the direction normal to the
        camera plane. Used if `position` is of length 2.
    value : float
        A default value of the characteristic of the particle. Used by
        optics unless a more direct property is set: (eg. `refractive_index`
        for `Brightfield` and `intensity` for `Fluorescence`).
    '''

    def __init__(self, **kwargs):
        super().__init__(upsample=1, upsample_axes=(), **kwargs)


    def get(self, image, **kwargs):

        return np.ones((1, 1, 1)) * 1.0


class Ellipse(Scatterer):
    '''Generates an elliptical disk scatterer

    Parameters
    ----------
    radius : float or array_like [float (, float)]
        Radius of the ellipse in meters. If only one value,
        assume circular.
    rotation : float
        Orientation angle of the ellipse in the camera plane in radians.
    position : array_like[float, float (, float)]
        The position of the particle. Third index is optional, 
        and represents the position in the direction normal to the
        camera plane.
    z : float
        The position in the direction normal to the
        camera plane. Used if `position` is of length 2.
    value : float
        A default value of the characteristic of the particle. Used by
        optics unless a more direct property is set: (eg. `refractive_index`
        for `Brightfield` and `intensity` for `Fluorescence`).
    upsample : int
        Upsamples the calculations of the pixel occupancy fraction.
    '''

    def __init__(self,
                radius,
                rotation,
                **kwargs):
        super().__init__(radius=radius, rotation=rotation, upsample_axes=(0, 1), **kwargs)
    

    def _process_properties(self, properties: dict) -> dict:
        '''Preprocess the input to the method .get()

        Ensures that the radius is an array of length 2. If the radius 
        is a single value, the particle is made circular
        '''

        properties = super()._process_properties(properties)

        # Ensure radius is of length 2
        radius = np.array(properties["radius"])
        if radius.ndim == 0:
            radius = np.array((properties["radius"], properties["radius"]))
        elif radius.size == 1:
            radius = np.array((*radius,) * 2)
        else:
            radius = radius[:2]
        properties["radius"] = radius

        return properties


    def get(self, *ignore, radius, rotation, voxel_size, **kwargs):
        
        # Create a grid to calculate on
        rad = radius[:2] / voxel_size[:2]
        ceil = int(np.max(np.ceil(rad)))
        X, Y = np.meshgrid(np.arange(-ceil, ceil), np.arange(-ceil, ceil))

        # Rotate the grid
        if rotation != 0:
            Xt =  (X * np.cos(-rotation) + Y * np.sin(-rotation))
            Yt = (-X * np.sin(-rotation) + Y * np.cos(-rotation))
            X = Xt
            Y = Yt 

        # Evaluate ellipse
        mask = ((X * X) / (rad[0] * rad[0]) + (Y * Y) / (rad[1] * rad[1]) < 1) * 1.0
        mask = np.expand_dims(mask, axis=-1)
        return mask



class Sphere(Scatterer):
    '''Generates a spherical scatterer

    Parameters
    ----------
    radius : float
        Radius of the sphere in meters.
    position : array_like[float, float (, float)]
        The position of the particle. Third index is optional, 
        and represents the position in the direction normal to the
        camera plane.
    z : float
        The position in the direction normal to the
        camera plane. Used if `position` is of length 2.
    value : float
        A default value of the characteristic of the particle. Used by
        optics unless a more direct property is set: (eg. `refractive_index`
        for `Brightfield` and `intensity` for `Fluorescence`).
    upsample : int
        Upsamples the calculations of the pixel occupancy fraction.
    '''

    def __init__(self,
                 radius,
                 **kwargs):
        super().__init__(radius=radius, **kwargs)


    def get(self, 
            image,
            radius,
            voxel_size,
            **kwargs):

        # Create a grid to calculate on
        rad = radius / voxel_size
        rad_ceil = np.ceil(rad)
        x = np.arange(-rad_ceil[0], rad_ceil[0])
        y = np.arange(-rad_ceil[1], rad_ceil[1])
        z = np.arange(-rad_ceil[2], rad_ceil[2])
        X, Y, Z = np.meshgrid((x / rad[0])**2, (y / rad[1])**2, (z / rad[2])**2)

        mask = (X + Y + Z <= 1) * 1.0
        return mask



class Ellipsoid(Scatterer):
    '''Generates an ellipsoidal scatterer

    Parameters
    ----------
    radius : float or array_like[float (, float, float)]
        Radius of the ellipsoid in meters. If only one value,
        assume spherical.
    rotation : float
        Rotation of the ellipsoid in about the x, y and z axis.
    position : array_like[float, float (, float)]
        The position of the particle. Third index is optional, 
        and represents the position in the direction normal to the
        camera plane.
    z : float
        The position in the direction normal to the
        camera plane. Used if `position` is of length 2.
    value : float
        A default value of the characteristic of the particle. Used by
        optics unless a more direct property is set: (eg. `refractive_index`
        for `Brightfield` and `intensity` for `Fluorescence`).
    upsample : int
        Upsamples the calculations of the pixel occupancy fraction.
    '''

    def __init__(self,
                 radius,
                 rotation=0,
                 **kwargs):
        super().__init__(radius=radius, rotation=rotation, **kwargs)

    
    def _process_properties(self, propertydict):
        '''Preprocess the input to the method .get()

        Ensures that the radius and the rotation properties both are arrays of
        length 3.

        If the radius is a single value, the particle is made a sphere
        If the radius are two values, the smallest value is appended as the third value

        The rotation vector is padded with zeros until it is of length 3
        '''

        # Ensure radius has three values
        radius = np.array(propertydict["radius"])
        if radius.ndim == 0:
            radius = np.array([radius])
        if radius.size == 1:
            # If only one value, assume sphere
            radius = (*radius,) * 3
        elif radius.size == 2:
            # If two values, duplicate the minor axis
            radius = (*radius, np.min(radius[-1]))
        elif radius.size == 3:
            # If three values, convert to tuple for consistency
            radius = (*radius, )
        propertydict["radius"] = radius

        # Ensure rotation has three values
        rotation = np.array(propertydict["rotation"])
        if rotation.ndim == 0:
            rotation = np.array([rotation])
        if rotation.size == 1:
            # If only one value, pad with two zeros
            rotation = (*rotation, 0, 0) 
        elif rotation.size == 2:
            # If two values, pad with one zero
            rotation = (*rotation, 0)
        elif rotation.size == 3:
            # If three values, convert to tuple for consistency
            rotation = (*rotation, )
        propertydict["rotation"] = rotation

        return propertydict


    def get(self,
            image,
            radius,
            rotation,
            voxel_size,
            **kwargs):

        radius_in_pixels = radius / voxel_size
        max_rad = np.max(radius) / voxel_size
        rad_ceil = np.ceil(max_rad)

        # Create grid to calculate on
        x = np.arange(-rad_ceil[0], rad_ceil[0])
        y = np.arange(-rad_ceil[1], rad_ceil[1])
        z = np.arange(-rad_ceil[2], rad_ceil[2])
        X, Y, Z = np.meshgrid(x, y, z)

        # Rotate the grid
        cos = np.cos(rotation)
        sin = np.sin(rotation)
        XR = (cos[0] * cos[1] * X) + (cos[0] * sin[1] * sin[2] - sin[0] * cos[2]) * Y + (cos[0] * sin[1] * cos[2] + sin[0] * sin[2]) * Z
        YR = (sin[0] * cos[1] * X) + (sin[0] * sin[1] * sin[2] + cos[0] * cos[2]) * Y + (sin[0] * sin[1] * cos[2] - cos[0] * sin[2]) * Z
        ZR = (-sin[1] * X) + cos[1] * sin[2] * Y + cos[1] * cos[2] * Z 

        mask = ((XR / radius_in_pixels[0])**2 + (YR / radius_in_pixels[1])**2 + (ZR / radius_in_pixels[2])**2 < 1) * 1.0
        return mask
