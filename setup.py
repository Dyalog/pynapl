from setuptools import setup

setup(
        name='APLPy',
        version='0.0.1.dev2',
        
        description='Python - Dyalog APL bridge',
        long_description="""
This package allows communication between Python and Dyalog APL.
""",
        
        url='TODO',
        
        author='TODO',
        author_email='TODO',

        license='TODO',

        classifiers=[
            'Development Status :: 2 - Pre-Alpha',

            'Intended Audience :: Developers',

            'Programming Language :: APL',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
        ],

        keywords='apl dyalog-apl bridge',

        packages=['aplpy'],

        package_data={
            'aplpy': [
                'Py.dyalog',
                'PyTest.dyalog',
                'WinPySlave.dyalog',
                'WinPySlave.dyapp'
            ]
        },
)
