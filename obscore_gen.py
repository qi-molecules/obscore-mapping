#!/usr/bin/env python3

from scipy.io import readsav
import numpy as np
import glob
import os
import sys
from astropy.io import fits
from datetime import datetime

def generate_obscore(meta_files, template_file, obscoredef_file, output_file):

    template_mapping = {}

    # Read the template mapping from the file
    print(f"Processing template file: {template_file} ...")
    #templatefile = 'templateMapping_SMA.txt'
    with open(template_file, 'r') as f:
        lines = f.readlines()

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                key, metadata, mapping = line.split(None, 2)
                if '$val' in mapping:
                    template_mapping[key.strip("'")] = mapping.strip("'").replace('$val', metadata.strip("'"))
                else:
                    template_mapping[key.strip("'")] = mapping.strip("'")


    # Create an empty dictionary
    result_dict = {}

    # Process each metadata file
    for savefile in glob.glob(meta_files):
        try:
            print(f"Processing meta files: {savefile} ...")
            # Read save file in Python
            data = readsav(savefile)

            # Assign each variable
            globals().update(data)

            # Extract all the keywords into a list
            keywords_list = list(data.keys())

            # Determine the size of the arrays
            first_key = keywords_list[0]
            array_size = np.size(data[first_key])

            # Process each key-value pair in the template mapping
            for key, equation in template_mapping.items():
                try:
                    if any(var in equation for var in keywords_list):
                        # Evaluate the equation using the arrays
                        values = eval(equation, data)
                        # Add the key-value pair to the result dictionary
                        result_dict.setdefault(key, []).extend(values)
                    else:
                        # Populate the array with the same size as other keys
                        values = np.full(array_size, equation)
                        # Add the key-value pair to the result dictionary
                        result_dict.setdefault(key, []).extend(values)
                except (ValueError, KeyError) as e:
                    print(f"Error processing key-value pair: {key}: {str(e)}")

                        # Add the savefile name to the result dictionary
                        #result_dict.setdefault('savename', []).extend([os.path.basename(savefile)] * array_size)

        except Exception as e:
            print(f"Error reading IDL save file: {str(e)}")

    # Print the resulting dictionary
    # print(result_dict)


    # Read the input file with keyword formatting
    print(f"Processing ObsCore definition file: {obscoredef_file} ...")
    with open(obscoredef_file, 'r') as f:
        lines = f.readlines()

    # Create a list to store the FITS columns
    fits_columns = []

    # Process each line in the keyinput file
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            keyword, formatcode, mandatory = line.split(None, 2)
            keyword = keyword.strip("'")
            formatcode = formatcode.strip("'")
            mandatory = True if mandatory.strip("'") == 'yes' else False

            try:
                # Check if the keyword exists in the result_dict
                if keyword not in result_dict:
                    if mandatory:
                        raise ValueError(f"Mandatory keyword '{keyword}' not found in the result_dict.")
                    else:
                        continue  # Skip non-mandatory keyword


                # Get the values for the keyword from the result_dict
                values = result_dict[keyword]
            
                # Create the FITS column based on the format code
                if formatcode == 'I':
                    column = fits.Column(name=keyword, format='I', array=values)
                elif formatcode == 'D':
                    column = fits.Column(name=keyword, format='D', array=values)
                elif formatcode == 'J':
                    column = fits.Column(name=keyword, format='J', array=values)
                elif formatcode == 'A':
                    column = fits.Column(name=keyword, format='A{}'.format(len(str(values))), array=[str(values)])
            
                # Append the FITS column to the list
                fits_columns.append(column)

            except (ValueError, KeyError) as e:
                print(f"Error: {str(e)}")

    # Create a FITS primary HDU with an empty data array
    primary_hdu = fits.PrimaryHDU()

    # Create a FITS table extension with the resulting dictionary as the data
    table_hdu = fits.BinTableHDU.from_columns(fits_columns)

    # Get the current date and time
    current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Add header keywords with input file names and code execution date and time
    primary_hdu.header['TEMPLATE'] = template_file
    primary_hdu.header['METAFILE'] = meta_files
    primary_hdu.header['DEFFILE'] = obscoredef_file
    primary_hdu.header['DATE'] = current_datetime

    # Create a FITS HDU list and append the primary and table HDUs
    hdul = fits.HDUList([primary_hdu, table_hdu])

    # Specify the output FITS file name
    print(f"Writing out to file: {output_file}")

    # Write the FITS file
    try:
        hdul.writeto(output_file, overwrite=True)
    except Exception as e:
        print(f"Error writing FITS file: {str(e)}")

if __name__ == "__main__":
    try:
        # Call the function with the arguments passed from command line
        generate_obscore(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    except IndexError:
        print("Warning: Four arguments required. Please provide metadata files, template mapping file, ObsCore definition file, and the output file.")
