# ADR-0077: Pydantic v2 Descriptor Compatibility

## Metadata
- **Status**: Accepted
- **Author**: Principal Engineer
- **Date**: 2025-12-16
- **Deciders**: Principal Engineer
- **Related**: ADR-0075 (Navigation Descriptors), ADR-0076 (Auto-Invalidation), TDD-HARDENING-C

## Context

Implementing the navigation descriptor pattern (ADR-0075) for `ParentRef[T]` and `HolderRef[T]` in Pydantic v2 models requires addressing two compatibility challenges:

### Challenge 1: Descriptor Class Attributes

Pydantic v2 interprets class attributes with type annotations as model fields:

```python
# This creates a Pydantic field, not a descriptor
business: Business | None = ParentRef[Business](holder_attr="_contact_holder")
```

Error: `PydanticUserError: A non-annotated attribute was detected`

### Challenge 2: Descriptor __set__ Method

Even when descriptors are properly declared, Pydantic v2's `__setattr__` intercepts attribute assignment and only delegates to `@property` objects, not generic descriptors:

```python
# Pydantic's __setattr__ raises ValueError for non-field attributes
child.business = new_business  # ValueError: "StubChild" object has no field "business"
```

### Forces at Play

1. **Type Safety**: IDE type inference via Generic[T] and @overload is valuable
2. **Descriptor Protocol**: Python's native descriptor protocol should work
3. **Pydantic Compatibility**: Models inherit from Task which inherits from BaseModel
4. **Auto-Invalidation**: ADR-0076 requires __set__ interception for invalidation triggers

## Decision

Configure `BusinessEntity.model_config` with two settings:

```python
class BusinessEntity(Task):
    model_config = ConfigDict(
        ignored_types=(ParentRef, HolderRef),
        extra="allow",
    )
```

### ignored_types

Tells Pydantic to ignore instances of `ParentRef` and `HolderRef` when processing class attributes. This allows descriptors to be declared without type annotations:

```python
class Contact(BusinessEntity):
    _business: Business | None = PrivateAttr(default=None)

    # No type annotation - Pydantic ignores this because ParentRef is in ignored_types
    business = ParentRef[Business](holder_attr="_contact_holder")
```

### extra="allow"

Allows setting attributes that aren't model fields. This enables Pydantic's `__setattr__` to delegate to descriptors rather than raising ValueError.

## Rationale

### Why ignored_types?

| Alternative | Pros | Cons |
|-------------|------|------|
| `ClassVar` annotation | Standard Pydantic pattern | ClassVars can't be assigned per-instance |
| Type annotation with Field() | Pydantic-native | Creates model field, not descriptor |
| No type annotation | Simple | Requires ignored_types to prevent error |

**Decision**: `ignored_types` with no type annotation because it allows descriptors to work as Python intended while Pydantic ignores them.

### Why extra="allow"?

| Alternative | Pros | Cons |
|-------------|------|------|
| Custom `__setattr__` | Full control | Complex, must handle all Pydantic cases |
| Property wrapper | Uses Pydantic's property detection | Adds indirection layer |
| `extra="allow"` | Simple config change | Allows any extra attributes |

**Decision**: `extra="allow"` because:
- Simple configuration
- Pydantic's `__setattr__` checks `extra` config before raising
- Side effect (allowing extra attrs) is acceptable for business entities

### Type Safety Preservation

Despite lacking type annotations on descriptor declarations, type safety is preserved through:

1. **Generic type parameter**: `ParentRef[Business]` carries type info
2. **@overload decorators**: IDE sees correct return type (`Business | None`)
3. **PrivateAttr still annotated**: Storage (`_business: Business | None`) has full typing

## Consequences

### Positive

1. **Descriptors work**: Both `__get__` and `__set__` function correctly
2. **IDE support**: Type hints via Generic[T] and @overload provide autocomplete
3. **Auto-invalidation enabled**: ADR-0076's __set__-triggered invalidation works
4. **Backward compatible**: Existing entities continue to work

### Negative

1. **Extra attributes allowed**: `entity.any_attr = value` won't raise
   - Mitigation: Business entities are internal; no external API exposure
2. **No descriptor type in annotation**: IDE shows `ParentRef[T]` not `T | None` for class access
   - Mitigation: Instance access shows correct type via @overload
3. **Slightly non-idiomatic**: Descriptors without type annotations is unusual
   - Mitigation: Pattern is documented in descriptors.py module docstring

### Neutral

1. **inherited from Task**: Parent model_config is extended, not replaced
2. **No API surface change**: External behavior unchanged

## Compliance

1. **Code Review Checklist**:
   - [ ] Descriptor declarations have NO type annotations
   - [ ] Corresponding PrivateAttr HAS type annotation
   - [ ] New BusinessEntity subclasses don't override model_config unsafely

2. **Testing**:
   - [ ] Descriptor __get__ returns correct value
   - [ ] Descriptor __set__ stores value and triggers invalidation
   - [ ] Model serialization excludes descriptors
