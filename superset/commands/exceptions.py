# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from typing import Any, Optional

from flask_babel import lazy_gettext as _
from marshmallow import ValidationError

from superset.exceptions import SupersetException


class CommandException(SupersetException):
    """Common base class for Command exceptions."""

    def __repr__(self) -> str:
        if self._exception:
            return repr(self._exception)
        return super().__repr__()


class ObjectNotFoundError(CommandException):
    status = 404
    message_format = "{} {}not found."

    def __init__(
        self,
        object_type: str,
        object_id: Optional[str] = None,
        exception: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            _(
                self.message_format.format(
                    object_type, f'"{object_id}" ' if object_id else ""
                )
            ),
            exception,
        )


class CommandInvalidError(CommandException):
    """Common base class for Command Invalid errors."""

    status = 422

    def __init__(
        self,
        message: str = "",
        exceptions: Optional[list[ValidationError]] = None,
    ) -> None:
        self._exceptions = exceptions or []
        super().__init__(message)

    def append(self, exception: ValidationError) -> None:
        self._exceptions.append(exception)

    def extend(self, exceptions: list[ValidationError]) -> None:
        self._exceptions.extend(exceptions)

    def get_list_classnames(self) -> list[str]:
        return sorted({ex.__class__.__name__ for ex in self._exceptions})

    def normalized_messages(self) -> dict[Any, Any]:
        errors: dict[Any, Any] = {}
        for exception in self._exceptions:
            errors.update(exception.normalized_messages())
        return errors


class UpdateFailedError(CommandException):
    status = 500
    message = "Command update failed"


class CreateFailedError(CommandException):
    status = 500
    message = "Command create failed"


class DeleteFailedError(CommandException):
    status = 500
    message = "Command delete failed"


class ForbiddenError(CommandException):
    status = 403
    message = "Action is forbidden"


class ImportFailedError(CommandException):
    status = 500
    message = "Import failed for an unknown reason"


class OwnersNotFoundValidationError(ValidationError):
    status = 422

    def __init__(self) -> None:
        super().__init__([_("Owners are invalid")], field_name="owners")


class RolesNotFoundValidationError(ValidationError):
    status = 422

    def __init__(self) -> None:
        super().__init__([_("Some roles do not exist")], field_name="roles")


class DatasourceTypeInvalidError(ValidationError):
    status = 422

    def __init__(self) -> None:
        super().__init__(
            [_("Datasource type is invalid")], field_name="datasource_type"
        )


class DatasourceNotFoundValidationError(ValidationError):
    status = 404

    def __init__(self) -> None:
        super().__init__([_("Datasource does not exist")], field_name="datasource_id")


class QueryNotFoundValidationError(ValidationError):
    status = 404

    def __init__(self) -> None:
        super().__init__([_("Query does not exist")], field_name="datasource_id")


class TagNotFoundValidationError(ValidationError):
    def __init__(self, message: str) -> None:
        super().__init__(message, field_name="tags")


class TagForbiddenError(ForbiddenError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
