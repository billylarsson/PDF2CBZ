![Screenshot from 2021-08-06 19-22-42](https://user-images.githubusercontent.com/59517785/128548948-def908ba-e77e-485d-b00f-b166369a53b4.png)

## PDF2CBZ v0.3.1-beta

### BUGFIXES
- single core WEBP-conversion not starting

### Description
Extracts images from PDF-files and converts them into WEBP-images and stores those inside a CBZ-file (essentially into a ZIP file renamed to CBZ). File naming logic is attempting to use the inputs file with the CBZ extension instead of PDF.

### Features
- **PDF-Threads** image extraction single or multiple core 
- **WEBP-Threads** single or multiple core
- **WEBP quality** adjustable
- **Continious checked** once que is empty another randomly file will automatically be processed, once all visible PDFs are converted next page is loaded automatically
- **4K checked** always shrinks wider images into 4K width  
- **DELETE PDF** after conversion is completed the PDF file is deleted (think before checking)
- **HIDDEN FEATURES** you can right-click the WEBP-QUALITY label to find som extras 

### Preparations
- pip install -r requirements.txt --user
- Recomend editing launcher.py just to get a glance at some settings

### Start program
- python3 launcher.py
- Assigning correct poppler path example: c:\Program Files\poppler-0.68.0\bin\ Compiled Poppler for Windows can be downloaded here: http://blog.alivate.com.au/poppler-windows/
- Enter source path containing PDF-files (recursive scans default)
- Enter destination path where CBZ-files will be stored
- Clicking any PDF inside the program automatically starts the conversion
- Clicking additional PDF files puts then in the conversion-que

### Also

**I run Linux only.** I cannot afford a Windows license nor a Mac computer therefore support for those are limited but any assumtion is that this should work on any of those.
