# HRMSV3_optimized/app/models/__init__.py

# This file makes the 'models' directory a Python package.
# Import models to make them easier to access
from .users import User, Role
from .employee import Employee
from .project import Project, Task
from .attendance import Attendance