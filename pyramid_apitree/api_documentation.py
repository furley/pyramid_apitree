""" Copyright (c) 2013 Josh Matthias <pyramid.apitree@gmail.com> """
import inspect
import json
import os.path
from mako.template import Template
from iomanager import ListOf
from iomanager.iomanager import NotProvided

from .view_callable import SimpleViewCallable
from .tree_scan import (
    ALL_REQUEST_METHODS,
    get_endpoints,
    )

INDENT_STR = '    '

class Error(Exception):
    """ Base class for errors. """

class PreparationFailureError(Error):
    """ A value failed to coerce to a string via the 'prepare' method. """

class APIDocumentationMaker(object):
    def __init__(self, api_tree={}, title='API Documentation'):
        self.documentation_dict = self.create_documentation(api_tree)
        self.documentation_title = title
        
        template_filename = os.path.join(
            os.path.dirname(__file__),
            'api_doc_template.mak',
            )
        
        self.documentation_html = Template(
            filename=template_filename,
            ).render(
            documentation_dict=self.documentation_dict,
            documentation_title = self.documentation_title,
            )
    
    def __call__(self, request):
        return self.documentation_html
    
    @staticmethod
    def indent(s):
        return '\n'.join([INDENT_STR + line for line in s.splitlines()])
    
    def prepare(self, value):
        if isinstance(value, (list, tuple)):
            return self.prepare_list(value)
        if isinstance(value, dict):
            return self.prepare_dict(value)
        if isinstance(value, ListOf):
            return self.prepare_listof(value)
        
        display_names = getattr(self, 'display_names', {})
        try:
            return display_names[value]
        except KeyError:
            return value.__name__
    
    def prepare_list(self, value):
        start, end = '[]'
        prepared_lines = map(self.prepare, value)
        all_lines = [start] + map(self.indent, prepared_lines) + [end]
        
        return '\n'.join(all_lines)
    
    def prepare_dict(self, value):
        start, end = '{}'
        prepared_lines = [
            "{}: {}".format(ikey, self.prepare(ivalue))
            for ikey, ivalue in value.iteritems()
            ]
        all_lines = [start] + map(self.indent, prepared_lines) + [end]
        
        return '\n'.join(all_lines)
    
    def prepare_listof(self, value):
        start, end = 'ListOf(', ')'
        
        iospec_obj = value.iospec_obj
        if not isinstance(iospec_obj, (list, dict)):
            joiner = ''
            wrapped = self.prepare(iospec_obj)
        else:
            joiner = '\n'
            wrapped = self.indent(self.prepare(iospec_obj))
        
        return joiner.join([start, wrapped, end])
    
    def create_documentation(self, api_tree):
        endpoints = get_endpoints(api_tree)
        
        types_to_skip = getattr(self, 'types_to_skip', [])
        
        result = {}
        for path, endpoint_list in endpoints.iteritems():
            path_methods = {}
            for item in endpoint_list:
                request_methods = item.get(
                    'request_method',
                    ALL_REQUEST_METHODS,
                    )
                method_key = ', '.join(request_methods)
                
                view_callable = item['view']
                if type(view_callable) in types_to_skip:
                    continue
                
                method_dict = {}
                
                method_dict['description'] = (
                    view_callable.wrapped.__doc__ or 'No description provided.'
                    )
                
                if hasattr(view_callable, 'manager'):
                    manager = view_callable.manager
                    
                    raw_iospecs = {
                        'required': manager.input_processor.required,
                        'optional': manager.input_processor.optional,
                        'returns': manager.output_processor.required,
                        }
                    
                    prepared_iospecs = {
                        ikey: self.prepare(ivalue)
                        for ikey, ivalue in raw_iospecs.iteritems()
                        if ivalue is not NotProvided and ivalue != {}
                        }
                    
                    if manager.input_processor.unlimited:
                        prepared_iospecs['unlimited'] = (
                            manager.input_processor.unlimited
                            )
                    
                    method_dict.update(prepared_iospecs)
                
                path_methods[method_key] = method_dict
            
            if path_methods:
                result[path] = path_methods
        
        return result
    
    @classmethod
    def scan_and_insert(
        cls,
        api_tree,
        path,
        view_class=SimpleViewCallable,
        **view_kwargs
        ):
        view_kwargs.setdefault('renderer', 'string')
        documentation_callable = cls(api_tree)
        view_callable = view_class(
            documentation_callable,
            **view_kwargs
            )
        api_tree.setdefault(path, {})
        api_tree[path]['GET'] = view_callable







