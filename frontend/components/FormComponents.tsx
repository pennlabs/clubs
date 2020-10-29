import { useFormikContext } from 'formik'
import React, { ReactElement, useContext, useEffect, useState } from 'react'
import Select from 'react-select'

import { titleize } from '../utils'
import { Icon } from './common'

interface BasicFormField {
  name: string
  label?: string
  helpText?: string
  placeholder?: string
  noLabel?: boolean
}

interface AnyHack {
  [key: string]: any
}

export const FormFieldClassContext = React.createContext<string>('')

export const useFieldWrapper = (Element): ((props: any) => ReactElement) => {
  return (props: React.PropsWithChildren<BasicFormField & AnyHack>) => {
    const { label, noLabel, helpText, ...other } = props
    const { status } = useFormikContext()
    const actualLabel = label ?? titleize(props.name)
    const errorMessage = status && status[props.name]
    const fieldContext = useContext(FormFieldClassContext)
    const isHorizontal = fieldContext.includes('is-horizontal')

    const fieldBody = (
      <>
        <div className="control">
          <Element {...other} isError={!!errorMessage} />
        </div>
        <p className={`help ${errorMessage ? 'is-danger' : ''}`}>
          {errorMessage ?? helpText}
        </p>
      </>
    )

    return (
      <div className={`field ${fieldContext}`}>
        {noLabel ||
          (isHorizontal ? (
            <div className="field-label">
              <label className="label">{actualLabel}</label>
            </div>
          ) : (
            <label className="label">{actualLabel}</label>
          ))}
        {isHorizontal ? (
          <div className="field-body">
            <div className="field">{fieldBody}</div>
          </div>
        ) : (
          fieldBody
        )}
      </div>
    )
  }
}

export const TextField = useFieldWrapper(
  (props: BasicFormField & AnyHack): ReactElement => {
    const { type = 'text', isError, value, ...other } = props

    return type === 'textarea' ? (
      <textarea
        className={`textarea ${isError ? 'is-danger' : ''}`}
        value={value ?? ''}
        {...other}
      ></textarea>
    ) : (
      <input
        className={`input ${isError ? 'is-danger' : ''}`}
        type={type}
        value={value != null ? value.toString() : ''}
        {...other}
      />
    )
  },
)

export const FileField = useFieldWrapper(
  ({
    name,
    placeholder,
    onBlur,
    value,
    isImage = false,
    canDelete = false,
  }: BasicFormField & AnyHack): ReactElement => {
    const { setFieldValue } = useFormikContext()

    const [imageUrl, setImageUrl] = useState<string | null>(null)
    const [newlyUploaded, setNewlyUploaded] = useState<boolean>(false)

    useEffect(() => {
      if (value == null) {
        setImageUrl(null)
        setNewlyUploaded(false)
      } else if (value instanceof File) {
        if (isImage) {
          const reader = new FileReader()
          reader.onload = (e) => {
            setImageUrl(e.target?.result as string)
          }
          reader.readAsDataURL(value)
          setNewlyUploaded(true)
        } else {
          setImageUrl(`FILE:${value.name}`)
        }
      } else {
        setImageUrl(value)
        setNewlyUploaded(false)
      }
    }, [value])

    return (
      <>
        {imageUrl &&
          (imageUrl.startsWith('FILE:') ? (
            <div className="mb-3">
              <Icon name="file" alt="file" /> {imageUrl.substr(5)}
            </div>
          ) : (
            <img style={{ width: 300 }} src={imageUrl} />
          ))}
        <div className="file">
          <label className="file-label">
            <input
              className="file-input"
              type="file"
              name={name}
              onChange={(e) => {
                setFieldValue(name, e.target.files ? e.target.files[0] : null)
              }}
              onBlur={onBlur}
              placeholder={placeholder}
            />
            <span className="file-cta">
              <span className="file-label">
                Choose a {isImage ? 'image' : 'file'}...
              </span>
            </span>
          </label>
          {imageUrl && (canDelete || isImage) && (
            <button
              onClick={() => {
                setFieldValue(name, null)
              }}
              className="ml-3 button is-danger"
            >
              <Icon name="trash" /> Remove {isImage ? 'Image' : 'File'}
            </button>
          )}
        </div>
        {newlyUploaded && (
          <p className="is-size-7">(Submit this form to confirm upload)</p>
        )}
      </>
    )
  },
)

export const MultiselectField = useFieldWrapper(
  ({
    name,
    choices,
    placeholder,
    value,
    onBlur,
  }: BasicFormField & AnyHack): ReactElement => {
    const { setFieldValue } = useFormikContext()

    const serialize = (opt) => {
      if (opt == null) {
        return []
      }
      return opt.map(({ value, label }) => ({
        id: value,
        name: label,
      }))
    }

    const deserialize = (opt) => {
      return opt.map((item) => {
        return { value: item.id ?? item.value, label: item.name ?? item.label }
      })
    }

    return (
      <Select
        key={name}
        placeholder={placeholder}
        isMulti={true}
        value={deserialize(value)}
        options={deserialize(choices)}
        onChange={(opt) => setFieldValue(name, serialize(opt))}
        onBlur={onBlur}
        styles={{ container: (style) => ({ ...style, width: '100%' }) }}
      />
    )
  },
)

export const CheckboxField = (
  props: BasicFormField & AnyHack,
): ReactElement => {
  const { label, value, ...other } = props
  const { status } = useFormikContext()
  const errorMessage = status && status[props.name]
  const fieldContext = useContext(FormFieldClassContext)
  const isHorizontal = fieldContext.includes('is-horizontal')

  const innerBody = (
    <>
      <div className="control">
        <label className="checkbox">
          <input type="checkbox" checked={value} {...other} /> {label}
        </label>
      </div>
      {errorMessage && <p className="help is-danger">{errorMessage}</p>}
    </>
  )

  return (
    <div className={`field ${fieldContext}`}>
      {isHorizontal ? (
        <>
          <div className="field-label">
            <label className="label">{titleize(props.name)}</label>
          </div>
          <div className="field-body">{innerBody}</div>
        </>
      ) : (
        innerBody
      )}
    </div>
  )
}
