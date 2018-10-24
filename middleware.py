import importlib
from urllib.parse import urlparse
from django.urls import resolve

from django.conf import settings

try:
    # Django versions >= 1.9
    from django.utils.module_loading import import_module
except ImportError:
    # Django versions < 1.9
    from django.utils.importlib import import_module

def get_class(module_name, cls_name):
    try:
        module = import_module(module_name)

    except ImportError:
        raise ImportError('Invalid class path: {}'.format(module_name))
    try:
        cls = getattr(module, cls_name)
    except AttributeError:
        pass

    else:
        return cls


class TestGenMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def process_view(self, request, view_func, view_args, view_kwargs):
        self.view_class = get_class(view_func.__module__, view_func.__name__)
        #self.process_(request, view_func)

        self.appname = view_func.__module__.rpartition('.')[0]
        self.testname = 'test_{0}_{1}'.format(self.appname, view_func.__name__)


    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)
        path = request.get_full_path()

        comment = '# {}'.format(request.get_full_path())

        if response.status_code == 500:
            return response

        if response.status_code == 302:
            print(1, self.view_class)

        if response.status_code == 404:
            p = path.split('/')[-1]
            if resolve(path.rstrip(p)):
                res = resolve(path.rstrip(p))
                self.appname = res.func.view_class.__module__.split('.')[0]
            self.testname = 'test_' + 'fail' + '_'+ str(response.status_code)


        # Code to be executed for each request/response after
        # the view is called.

        if request.user != "AnonymousUser":
            self.testname +='_auth'
            aut = \
'''c = Client()
        c.login(username='test', password='test')'''
        else:
            aut = ''

        template_cls = '''
    def {}(self):
        {}
        {}
        response = self.client.get('{}', follow=True)
        self.assertEqual(response.status_code, {})

    '''.format(self.testname, comment, aut, request.get_full_path(), response.status_code)

        #print(template_cls)

        testsfile = importlib.util.find_spec(name=self.appname + '.tests')
        with open(testsfile.origin, 'r') as f:
            content = f.read()

        if not "(TestCase)" in content:
            content += "\nclass GeneratedTests(TestCase):\n"

        if not self.testname in content:
            content += template_cls

        if self.appname in settings.TESTGEN_APPS:
            with open(testsfile.origin, 'w') as f:
                f.write(content)
        else:
            print(content, )



        return response

