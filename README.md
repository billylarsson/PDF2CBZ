![Screenshot from 2021-08-06 19-22-42](https://user-images.githubusercontent.com/59517785/128548948-def908ba-e77e-485d-b00f-b166369a53b4.png)

Converts PDF to WEBP Images that are put together into a CBZ file (essentially a ZIP-file containing the images)

Preparations:
pip install -r requirements.txt --user

Start the program by running: python main.py

Assigning correct poppler path example: c:\Program Files\poppler-0.68.0\bin\
Compiled Poppler for Windows can be downloaded here: http://blog.alivate.com.au/poppler-windows/

Enter source path to you PDF-files
Enter destination path where the CBZ-files shall be stored

Start converting by clicking the files you want to convert and they will added to the convertion que.
Program built to optimize speed, all CPU's are used.

File naming will be same as input(-PDF) + CBZ
