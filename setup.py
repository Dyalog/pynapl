from setuptools import setup

setup(
        name="Py'n'APL",
        version='0.1.0',
        
        description='Python - Dyalog APL interface',
        long_description="""
This package allows communication between Python and Dyalog APL.
""",
        
        url='https://github.com/marinuso/pynapl',
        
        author='TODO',
        author_email='TODO',

        license='TODO',

        classifiers=[
            'Development Status :: 3 - Alpha',

            'Intended Audience :: Developers',

            'Programming Language :: APL',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7'
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Programming Language :: Python :: 3.6',
        ],

        keywords='apl dyalog-apl interface',

        packages=['pynapl'],

        package_data={
            'pynapl': [
                'Py.dyalog',
                'PyTest.dyalog',
                'WinPySlave.dyalog',
                'IPC.dyalog',
                'WinPySlave.dyapp'
            ]
        },
)
