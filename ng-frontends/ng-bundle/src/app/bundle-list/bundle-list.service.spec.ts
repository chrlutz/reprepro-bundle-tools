/***********************************************************************
* Copyright (c) 2018 Landeshauptstadt München
*           (c) 2018 Christoph Lutz (InterFace AG)
*
* This program is free software: you can redistribute it and/or modify
* it under the terms of the European Union Public Licence (EUPL),
* version 1.1 (or any later version).
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* European Union Public Licence for more details.
*
* You should have received a copy of the European Union Public Licence
* along with this program. If not, see
* https://joinup.ec.europa.eu/collection/eupl/eupl-text-11-12
***********************************************************************/

import { TestBed } from "@angular/core/testing";

import { BundleListService } from "./bundle-list.service";
import { HttpClientModule } from "@angular/common/http";

describe("BundleListService", () => {
  beforeEach(() => TestBed.configureTestingModule({
    imports: [HttpClientModule] // should be replaced by HttpClientTestingModule
  }));

  it("should be created", () => {
    const service: BundleListService = TestBed.get(BundleListService);
    expect(service).toBeTruthy();
  });
});
