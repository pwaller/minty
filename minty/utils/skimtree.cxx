#ifndef __CINT__
#undef _POSIX_C_SOURCE
#include <Python.h>
#endif

#include <TPython.h>
#include <TTree.h>

#include <iostream>
using namespace std;

int skimtree(TTree* input, TTree* output, PyObject* eventlist)
{
    PyObject* iterator = PyObject_GetIter(eventlist);
    PyObject* item = NULL;
    if (!iterator) goto error;
    while ((item = PyIter_Next(iterator))) {
        if (!PyLong_Check(item)) goto error;
        cout << "Here!" << endl;
        input->GetEntry(PyLong_AsLongLong(item));
        output->Fill();
        Py_DECREF(item);
    }
    Py_DECREF(iterator);
    return 1;
error:
    Py_DECREF(item);
    Py_DECREF(iterator);
    return 0;
}
