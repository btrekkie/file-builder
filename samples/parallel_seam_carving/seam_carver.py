from PIL import Image


class SeamCarver:
    """Performs seam carving on an image.

    Each instance of ``SeamCarver`` may be used to carve a single image.
    See ``carve``.

    For the purposes of this sample project, it is not necessary to
    understand the implementation of ``SeamCarver``. It has no bearing
    on the approach ``ParallelSeamCarveBuilder`` uses to parallelize a
    build process.
    """

    # Private attributes:
    #
    # int _height - The height of the image we are carving.
    # list<tuple<int, int, int>> _pixels - The colors of the pixels of the
    #     image we are carving. This represents the pixels as (red, green,
    #     blue) tuples in row-major order. Each component is in the range [0,
    #     255].
    # list<int> _pixels_energy - The energy of the pixels of the image we are
    #     carving. The energy values are stored in row-major order.
    # int _width - The width of the image we are carving. This decreases as we
    #     carve the image.

    def carve(self, image, new_width):
        """Return the result of performing seam carving on the specified image.

        The returned image has a smaller width.

        Arguments:
            image (Image): The image to carve.
            new_width (int): The resulting image width. If this is
                greater than or equal to the current width, then carving
                has no effect.

        Returns:
            Image: The carved image.
        """
        # Extract image data
        width = image.width
        height = image.height
        self._width = width
        self._height = height
        self._pixels = []
        converted_image = image.convert('RGB')
        for y in range(height):
            for x in range(width):
                self._pixels.append(converted_image.getpixel((x, y)))

        # Compute _pixels_energy
        self._pixels_energy = []
        for y in range(height):
            for x in range(width):
                self._pixels_energy.append(self._compute_pixel_energy(x, y))

        # Carve the image
        while self._width > new_width:
            self._carve_once()

        # Convert the results to an Image
        output = Image.new('RGB', (self._width, height))
        output.putdata(self._pixels)
        return output

    def _compute_pixel_energy(self, x, y):
        """Return the energy of the specified pixel.

        This computes the energy rather than checking
        ``_pixels_energy``. At present, the energy is based on the
        colors of the adjacent pixels, including diagonally adjacent
        pixels.

        Arguments:
            x (int): The pixel's x coordinate.
            y (int): The pixel's y coordinate.

        Returns:
            int: The energy.
        """
        # A pixel's energy is determined using the following convolution
        # matrices:
        #
        #      [1 0 -1]         [ 1  2  1]
        # Mx = [2 0 -2]    My = [ 0  0  0]
        #      [1 0 -1]         [-1 -2 -1]
        #
        # If this doesn't make sense to you, then ignore it and read the
        # implementation.
        width = self._width
        index = width * y + x
        if x > 0:
            left_delta = -1
        else:
            left_delta = 0
        if x + 1 < width:
            right_delta = 1
        else:
            right_delta = 0
        if y > 0:
            up_delta = -width
        else:
            up_delta = 0
        if y + 1 < self._height:
            down_delta = width
        else:
            down_delta = 0

        # Read the adjacent pixels
        pixel11 = self._pixels[index + up_delta + left_delta]
        pixel21 = self._pixels[index + up_delta]
        pixel31 = self._pixels[index + up_delta + right_delta]
        pixel12 = self._pixels[index + left_delta]
        pixel32 = self._pixels[index + right_delta]
        pixel13 = self._pixels[index + down_delta + left_delta]
        pixel23 = self._pixels[index + down_delta]
        pixel33 = self._pixels[index + down_delta + right_delta]

        # Compute the energy
        energy = 0
        for i in range(3):
            energy += abs(
                pixel11[i] + 2 * pixel12[i] + pixel13[i] -
                pixel31[i] - 2 * pixel32[i] - pixel33[i])
            energy += abs(
                pixel11[i] + 2 * pixel21[i] + pixel31[i] -
                pixel13[i] - 2 * pixel23[i] - pixel33[i])
        return energy

    def _compute_seam(self):
        """Return a seam with the lowest energy.

        A "seam" is defined as a set of one pixel per row, with pixels
        in adjacent rows having x coordinates that differ by at most 1.
        A seam's energy is the sum of the energies of its pixels.

        Returns:
            list<int>: The seam. This contains the x coordinates of the
                seam's pixels from top to bottom.
        """
        # This is implemented using dynamic programming. We compute a list
        # subseam_energy that contains one energy value for each pixel. For
        # each pixel, it indicates the lowest energy for a subseam from the top
        # of the image to the pixel in question.

        # Compute subseam_energy
        width = self._width
        height = self._height
        subseam_energy = self._pixels_energy[:width]
        index = width
        for y in range(1, height):
            # Compute the subseam energy for (0, y)
            energy = subseam_energy[index - width]
            if width == 1:
                right_energy = None
                best_energy = energy
            else:
                right_energy = subseam_energy[index - width + 1]
                best_energy = min(energy, right_energy)
            subseam_energy.append(self._pixels_energy[index] + best_energy)
            index += 1

            # Compute the subseam energy for (x, y), where 0 < x < width - 1
            for x in range(1, width - 1):
                left_energy = energy
                energy = right_energy
                right_energy = subseam_energy[index - width + 1]

                # Apparently, this is faster than min(left_energy, energy,
                # right_energy)
                if left_energy < energy and left_energy < right_energy:
                    min_energy = left_energy
                elif energy < right_energy:
                    min_energy = energy
                else:
                    min_energy = right_energy

                subseam_energy.append(self._pixels_energy[index] + min_energy)
                index += 1

            # Compute the subseam energy for (width - 1, y)
            if width > 1:
                subseam_energy.append(
                    self._pixels_energy[index] + min(left_energy, energy))
                index += 1

        # Find the best x coordinate in the bottom row
        best_x = 0
        best_energy = subseam_energy[width * (height - 1)]
        for x in range(1, width):
            energy = subseam_energy[width * (height - 1) + x]
            if energy < best_energy:
                best_x = x
                best_energy = energy

        # Compute the seam by moving from bottom to top
        reversed_seam = [best_x]
        x = best_x
        for y in range(height - 1, 0, -1):
            index = width * (y - 1) + x
            energy = subseam_energy[index]
            next_x = x

            if x > 0:
                left_energy = subseam_energy[index - 1]
                if left_energy < energy:
                    next_x = x - 1
                    energy = left_energy

            if x + 1 < width:
                right_energy = subseam_energy[index + 1]
                if right_energy < energy:
                    next_x = x + 1
                    energy = right_energy

            reversed_seam.append(next_x)
            x = next_x
        return list(reversed(reversed_seam))

    def _carve_once(self):
        """Carve a single seam from the image.

        This reduces the width of the image by one. It alters
        ``_width``, ``_pixels``, and ``_pixels_energy``.
        """
        # Compute the seam
        width = self._width
        height = self._height
        seam = self._compute_seam()

        # Remove the seam
        new_pixels = []
        new_pixels_energy = []
        for y, x in enumerate(seam):
            new_pixels.extend(
                self._pixels[width * y:width * y + x])
            new_pixels.extend(
                self._pixels[width * y + x + 1:width * (y + 1)])
            new_pixels_energy.extend(
                self._pixels_energy[width * y:width * y + x])
            new_pixels_energy.extend(
                self._pixels_energy[width * y + x + 1:width * (y + 1)])
        self._pixels = new_pixels
        self._pixels_energy = new_pixels_energy
        width -= 1
        self._width = width

        # Recompute the energy of the pixels adjacent to the seam
        for y in range(height):
            x = seam[y]
            if ((y > 0 and seam[y - 1] == x - 1) or
                    (y + 1 < height and seam[y + 1] == x - 1)):
                min_x = max(0, x - 2)
            else:
                min_x = max(0, x - 1)

            if ((y > 0 and seam[y - 1] == x + 1) or
                    (y + 1 < height and seam[y + 1] == x + 1)):
                max_x = min(width - 1, x + 2)
            else:
                max_x = min(width - 1, x + 1)

            for update_x in range(min_x, max_x + 1):
                self._pixels_energy[width * y + update_x] = (
                    self._compute_pixel_energy(update_x, y))
