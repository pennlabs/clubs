import { Form, Formik } from 'formik'
import { ReactElement, useEffect, useMemo, useState } from 'react'
import styled from 'styled-components'

import { doApiRequest, formatResponse } from '../utils'
import { Icon, Loading } from './common'
import Table from './common/Table'
import { FormStyle } from './FormComponents'

const ModelItem = styled.div`
  padding: 15px;
  border: 1px solid #dbdbdb;
  border-radius: 3px;
  margin-bottom: 1em;
`

const ModelStatusWrapper = styled.span`
  display: inline-block;
  margin: 0.375em 0.75em;
`

const ModelStatus = ({ status }) => (
  <ModelStatusWrapper>
    {typeof status !== 'undefined' &&
      (status === true ? (
        <span style={{ color: 'green' }}>
          <Icon name="check-circle" alt="success" /> Saved!
        </span>
      ) : (
        <span style={{ color: 'red' }}>
          <Icon name="x-circle" alt="failure" /> Failed to save!
        </span>
      ))}
  </ModelStatusWrapper>
)

const Subtitle = styled.div`
  font-weight: bold;
  font-size: 1.2em;
  margin-bottom: 0.75em;
`

type ModelObject = { [key: string]: any }

type TableField = {
  label?: string
  name: string
  converter?: (field: any, object: ModelObject) => any
  render?: (field: any, object: number) => any
  id?: string
}

type Option = {
  label: string
  key: any
}

type FilterOption = {
  options: Option[]
  label: string
  filterFunction: (a, b) => boolean
}

type ModelFormProps = {
  listParams?: string
  initialData?: ModelObject[]
  baseUrl: string
  keyField?: string
  onUpdate?: (objects: ModelObject[]) => void
  onChange?: (object: ModelObject) => void
  defaultObject?: ModelObject
  fileFields?: string[]
  empty?: ReactElement | string
  fields: any
  tableFields?: TableField[]
  filterOptions?: FilterOption[]
  currentTitle?: (object: ModelObject) => ReactElement | string
  noun?: string
  deleteVerb?: string
  allowCreation?: boolean
  allowEditing?: boolean
  allowDeletion?: boolean
  confirmDeletion?: boolean
  actions?: (object: ModelObject) => ReactElement
}

/**
 * The initial values returned by Django usually have a "field_url" attribute for some field,
 * instead of "field", where field is a file or image field. In these cases, we modify
 * the field to remove this suffix if the field does not exist in the data.
 */
export const doFormikInitialValueFixes = (currentObject: {
  [key: string]: any
}): { [key: string]: any } => {
  if (currentObject == null) {
    return {}
  }
  return Object.entries(currentObject).reduce((prev, [key, val]) => {
    if (key.endsWith('_url')) {
      const otherKey = key.substr(0, key.length - 4)
      if (!(otherKey in prev)) {
        prev[otherKey] = val
      }
    }
    prev[key] = val
    return prev
  }, {})
}

type ModelTableProps = {
  tableFields: TableField[]
  filterOptions?: FilterOption[]
  objects: ModelObject[]
  allowEditing?: boolean
  allowDeletion?: boolean
  confirmDeletion?: boolean
  noun?: string
  deleteVerb?: string
  onEdit?: (object: ModelObject) => void
  onDelete?: (object: ModelObject) => void
  actions?: (object: ModelObject) => ReactElement
}

/**
 * Render a list of objects as a table.
 */
export const ModelTable = ({
  tableFields,
  filterOptions,
  objects,
  allowEditing = false,
  allowDeletion = false,
  confirmDeletion = false,
  noun = 'Object',
  deleteVerb = 'Delete',
  onEdit = () => undefined,
  onDelete = () => undefined,
  actions,
}: ModelTableProps): ReactElement => {
  const columns = useMemo(
    () =>
      tableFields.map(({ label, name }) => ({
        Header: label ?? name,
        accessor: name,
      })),
    [tableFields],
  )

  tableFields = tableFields.map((column, index) => {
    if (column.converter) {
      const renderFunction = column.converter
      return {
        ...column,
        render: (id) => {
          const obj = objects?.filter((item) => item.id === id)[0]
            ? objects?.filter((item) => item.id === id)[0]
            : objects?.[id]
          const value = obj?.[column.name]
          return obj && !(value === null) && !(value === undefined)
            ? renderFunction(value, obj)
            : 'N/A'
        },
      }
    } else return column
  })

  tableFields.push({
    name: 'Actions',
    render: (_, index) => (
      <div className="buttons">
        {allowEditing && (
          <button
            onClick={() => {
              return onEdit(objects[index])
            }}
            className="button is-primary is-small"
          >
            <Icon name="edit" alt="edit" /> Edit
          </button>
        )}
        {allowDeletion && (
          <button
            onClick={() => {
              if (confirmDeletion) {
                if (
                  confirm(
                    `Are you sure you want to ${deleteVerb.toLowerCase()} this ${noun.toLowerCase()}?`,
                  )
                ) {
                  onDelete(objects[index])
                }
              } else {
                onDelete(objects[index])
              }
            }}
            className="button is-danger is-small"
          >
            <Icon name="trash" alt="delete" /> {deleteVerb}
          </button>
        )}
        {actions && actions(objects[index])}
      </div>
    ),
  })

  return (
    <>
      <Table
        data={objects.map((item, index) =>
          item.id ? item : { ...item, id: index },
        )}
        columns={tableFields}
        searchableColumns={['name']}
        filterOptions={filterOptions || []}
      />
    </>
  )
}

/*
 * Creates a form with CRUD (create, read, update, delete)
 * capabilities for a Django model using a provided endpoint.
 */
export const ModelForm = (props: ModelFormProps): ReactElement => {
  const [objects, changeObjects] = useState<ModelObject[]>([])
  const [
    currentlyEditing,
    changeCurrentlyEditing,
  ] = useState<ModelObject | null>(null)
  const [newCount, changeNewCount] = useState<number>(0)
  const [createObject, changeCreateObject] = useState<ModelObject>(
    props.defaultObject != null ? { ...props.defaultObject } : {},
  )

  const {
    fields,
    tableFields,
    filterOptions,
    onUpdate,
    currentTitle,
    noun = 'Object',
    deleteVerb = 'Delete',
    allowCreation = true,
    allowEditing = true,
    allowDeletion = true,
    confirmDeletion = false,
    actions,
    keyField = 'id',
    onChange: parentComponentChange,
  } = props

  /**
   * This is called when the create/edit form has its contents changed.
   */
  const onChange = (obj): void => {
    if (props.onChange) {
      props.onChange(obj)
    }
  }

  /**
   * Called when the user wants to create a new object.
   * Does not save the object to the database.
   */
  const onCreate = (): void => {
    const newObjects: ModelObject[] = objects
    newObjects.push({
      tempId: newCount,
      ...(props.defaultObject ?? {}),
    })
    changeObjects(newObjects)
    changeNewCount(newCount + 1)
  }

  /**
   * Called when the user requests for an object to be deleted.
   * @param object The object that should be deleted.
   */
  const onDelete = (object): void => {
    const { baseUrl, keyField = 'id' } = props

    if (typeof object[keyField] !== 'undefined') {
      doApiRequest(`${baseUrl}${object[keyField]}/?format=json`, {
        method: 'DELETE',
      }).then((resp) => {
        if (resp.ok) {
          const newObjects: ModelObject[] = [...objects]
          newObjects.splice(objects.indexOf(object), 1)
          changeObjects(newObjects)
          if (onUpdate) onUpdate(newObjects)
        }
      })
    } else {
      const newObjects: ModelObject[] = [...objects]
      newObjects.splice(objects.indexOf(object), 1)
      changeObjects(newObjects)
      if (onUpdate) onUpdate(newObjects)
    }
  }

  /**
   * Called when the form is submitted to save an individual object.
   * @returns a promise with the first argument as the new object values.
   */
  const onSubmit = async (
    object: ModelObject | null,
    data,
  ): Promise<ModelObject> => {
    const { baseUrl, keyField = 'id' } = props

    // if object was deleted, return
    if (object == null) {
      return new Promise((resolve) => {
        resolve({
          _status: false,
          _errorMessage:
            'This object has already been deleted and cannot be saved.',
        })
      })
    }

    const formData = Object.keys(data).reduce((flt, key) => {
      if (
        !(data[key] instanceof File) &&
        !(
          props.fileFields &&
          props.fileFields.includes(key) &&
          data[key] !== null
        )
      ) {
        flt[key] = data[key]
      }
      return flt
    }, {})

    // create or edit the object, uploading all non-file fields
    const savePromise =
      typeof object[keyField] === 'undefined'
        ? doApiRequest(`${baseUrl}?format=json`, {
            method: 'POST',
            body: formData,
          })
        : doApiRequest(`${baseUrl}${object[keyField]}/?format=json`, {
            method: 'PATCH',
            body: formData,
          })

    // parse response
    const resp = await savePromise
    const json = await resp.json()
    object._status = resp.ok
    if (object._status) {
      Object.keys(json).forEach((key) => {
        object[key] = json[key]
      })
      object._errorMessage = null
    } else {
      object._errorMessage = json
    }
    const newObject = { ...object }

    // update object state
    changeObjects((objects) => {
      const objIndex = objects.indexOf(newObject)
      if (objIndex !== -1) {
        objects[objIndex] = newObject
      }
      return [...objects]
    })

    // upload all files in the form
    await Promise.all(
      Object.entries(data)
        .map(([key, value]) => {
          if (!(value instanceof File)) {
            return null
          }
          const fieldData = new FormData()
          fieldData.append(key, value)
          return doApiRequest(`${baseUrl}${object[keyField]}/?format=json`, {
            method: 'PATCH',
            body: fieldData,
          })
        })
        .filter((a) => a !== null),
    )
    return newObject
  }

  /**
   * Download the latest list of objects when the component is mounted.
   */
  useEffect(() => {
    doApiRequest(`${props.baseUrl}?format=json${props.listParams ?? ''}`)
      .then((resp) => resp.json())
      .then((resp) => {
        changeObjects(resp)
        if (onUpdate) onUpdate(resp)
      })
  }, [])

  if (!objects) {
    return <Loading />
  }

  if (tableFields) {
    const currentObjectIndex =
      currentlyEditing === null
        ? -1
        : objects.findIndex((a) => a[keyField] === currentlyEditing)
    const currentObject =
      currentlyEditing === null ? createObject : objects[currentObjectIndex]

    return (
      <>
        <ModelTable
          onEdit={(object): void => {
            changeCurrentlyEditing(object[keyField])
            onChange(object)
          }}
          onDelete={onDelete}
          deleteVerb={deleteVerb}
          noun={noun}
          tableFields={tableFields}
          filterOptions={filterOptions}
          objects={objects}
          allowDeletion={allowDeletion}
          confirmDeletion={confirmDeletion}
          allowEditing={allowEditing}
          actions={actions}
        />
        {(allowCreation || currentlyEditing !== null) && (
          <>
            <Subtitle>
              {currentlyEditing !== null ? 'Edit' : 'Create'} {noun}{' '}
              {currentTitle && currentlyEditing !== null && (
                <span style={{ color: '#888', fontSize: '0.8em' }}>
                  {currentTitle(currentObject)}
                </span>
              )}
            </Subtitle>
            <Formik
              validate={parentComponentChange}
              initialValues={doFormikInitialValueFixes(currentObject)}
              initialStatus={
                currentObject &&
                currentObject._status === false &&
                currentObject._errorMessage
              }
              onSubmit={(data) => {
                if (currentObjectIndex !== -1) {
                  objects[currentObjectIndex] = currentObject
                }
                onSubmit(currentObject, data).then((obj: ModelObject) => {
                  if (obj._status) {
                    if (currentlyEditing === null) {
                      objects.push(obj)
                    }
                    changeObjects([...objects])
                    if (onUpdate) onUpdate(objects)
                    changeCurrentlyEditing(obj[keyField])
                    changeCreateObject(
                      props.defaultObject != null
                        ? { ...props.defaultObject }
                        : {},
                    )
                  } else {
                    changeCreateObject(obj)
                  }
                })
              }}
              enableReinitialize
            >
              {({ isSubmitting }) => (
                <Form>
                  <FormStyle isHorizontal>
                    {fields}
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="button is-primary"
                    >
                      {currentlyEditing !== null ? (
                        <>
                          <Icon name="edit" alt="save" /> Save
                        </>
                      ) : (
                        <>
                          <Icon name="plus" alt="create" /> Create
                        </>
                      )}
                    </button>

                    {currentlyEditing !== null && (
                      <span
                        onClick={() => {
                          changeCreateObject(
                            props.defaultObject != null
                              ? { ...props.defaultObject }
                              : {},
                          )
                          changeCurrentlyEditing(null)
                          onChange({})
                        }}
                        className="button is-primary is-pulled-right"
                      >
                        {allowCreation ? (
                          <>
                            <Icon name="plus" alt="create" /> Create New
                          </>
                        ) : (
                          <>
                            <Icon name="x" alt="close" /> Close
                          </>
                        )}
                      </span>
                    )}
                    <ModelStatus status={currentObject?._status} />
                  </FormStyle>
                </Form>
              )}
            </Formik>
          </>
        )}

        {currentObject?._errorMessage && (
          <div style={{ color: 'red', marginTop: '1rem' }}>
            <Icon name="alert-circle" />{' '}
            {typeof currentObject._errorMessage === 'object' &&
              'Errors occured while processing your request:'}
            {formatResponse(currentObject._errorMessage)}
          </div>
        )}
      </>
    )
  }

  // card view
  return (
    <>
      {objects.map((object) => (
        <ModelItem
          key={
            typeof object[keyField] === 'undefined'
              ? `new-${object.tempId}`
              : object[keyField]
          }
        >
          <Formik
            initialValues={doFormikInitialValueFixes(object)}
            initialStatus={
              object && object._status === false && object._errorMessage
            }
            onSubmit={(data) => onSubmit(object, data)}
            enableReinitialize
          >
            {({ isSubmitting }) => (
              <Form>
                <FormStyle isHorizontal>
                  {fields}
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="button is-primary"
                  >
                    <Icon name="edit" alt="save" /> Save
                  </button>
                  {allowDeletion && (
                    <span
                      className="button is-danger"
                      style={{ marginLeft: '0.5em' }}
                      onClick={() => {
                        onDelete(object)
                      }}
                    >
                      <Icon name="trash" alt="trash" /> Delete
                    </span>
                  )}
                  <ModelStatus status={object._status} />
                </FormStyle>
              </Form>
            )}
          </Formik>
        </ModelItem>
      ))}
      {allowCreation && (
        <span onClick={onCreate} className="button is-primary">
          <Icon name="plus" alt="create" /> Create
        </span>
      )}
      {objects.length === 0 && props.empty}
    </>
  )
}

export default ModelForm
