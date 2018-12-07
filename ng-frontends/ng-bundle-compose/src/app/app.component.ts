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

import { Component, OnInit, OnDestroy, HostListener } from "@angular/core";
import { BackendRegisterService } from "shared";
import localeDe from "@angular/common/locales/de";
import { registerLocaleData } from "@angular/common";

registerLocaleData(localeDe, "de");

@Component({
  selector: "app-root",
  templateUrl: "./app.component.html",
  styleUrls: ["./app.component.css"]
})
export class AppComponent implements OnInit, OnDestroy {
  title = "ng-bundle-compose";
  hlB = false;

  constructor(private backend: BackendRegisterService) {}

  ngOnInit(): void {
    this.backend.registerOnBackend();
  }

  ngOnDestroy(): void {
    this.backend.unregisterFromBackend();
  }

  @HostListener("window:beforeunload", ["$event"])
  private _storeSettings($event: any = null): void {
    this.backend.unregisterFromBackend();
  }
}
