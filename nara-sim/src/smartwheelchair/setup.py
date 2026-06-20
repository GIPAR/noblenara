from setuptools import setup
from glob import glob
import os

package_name = 'smartwheelchair'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),

        # Launch files
        (os.path.join('share', package_name, 'launch'), glob('launch/*')),

        # Config files
        (os.path.join('share', package_name, 'config'), glob('config/*')),

        # URDF / Xacro / Gazebo robot files
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*')),

        # Worlds
        (os.path.join('share', package_name, 'worlds'), glob('worlds/*')),

        # Maps
        (os.path.join('share', package_name, 'maps'), glob('maps/*')),

        # Meshes
        (os.path.join('share', package_name, 'meshes'), glob('meshes/*')),

        # Models (top-level files, if any)
        (os.path.join('share', package_name, 'models'), glob('models/*')),

        # Model subfolders
        (os.path.join('share', package_name, 'models', 'iscas_museum'), glob('models/iscas_museum/*')),
        (os.path.join('share', package_name, 'models', 'iscas_museum', 'meshes'), glob('models/iscas_museum/meshes/*')),
        (os.path.join('share', package_name, 'models', 'iscas_museum', 'materials', 'textures'), glob('models/iscas_museum/materials/textures/*')),

        (os.path.join('share', package_name, 'models', 'person_standing'), glob('models/person_standing/*')),
        (os.path.join('share', package_name, 'models', 'person_standing', 'meshes'), glob('models/person_standing/meshes/*')),
        (os.path.join('share', package_name, 'models', 'person_standing', 'materials', 'textures'), glob('models/person_standing/materials/textures/*')),

        (os.path.join('share', package_name, 'models', 'person_walking'), glob('models/person_walking/*')),
        (os.path.join('share', package_name, 'models', 'person_walking', 'meshes'), glob('models/person_walking/meshes/*')),
        (os.path.join('share', package_name, 'models', 'person_walking', 'materials', 'textures'), glob('models/person_walking/materials/textures/*')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='seu_nome',
    maintainer_email='seu_email@example.com',
    description='Descrição do pacote',
    license='Apache License 2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'meu_script = meu_pacote.meu_script:main',
        ],
    },
)
