import { BundleListService } from "./bundle-list.service";
import { ServerLogComponent } from "./../server-log/server-log.component";
import { Component, OnInit, SystemJsNgModuleLoader } from "@angular/core";
import { IBundleListItem } from "../shared/bundle-list-item.interface";

@Component({
  selector: "bundle-list",
  templateUrl: "./bundle-list.component.html",
  styleUrls: ["./bundle-list.component.css"]
})
export class BundleListComponent implements OnInit {
  selectedDistribution = new Set<string>();
  selectedState = new Set<string>();
  selectedTarget = new Set<string>();
  selectedCreator = new Set<string>();
  bundles: IBundleListItem[] = [];

  constructor(private bundleListService: BundleListService) {}

  ngOnInit() {
    this.update();
  }

  update() {
    this.bundleListService.getBundleList().subscribe(
      (bundles: IBundleListItem[]) => {
        this.bundles = bundles;
      },
      errResp => {
        console.error('Error loading bundle list', errResp);
      }
    );
  }

  getBundles(): IBundleListItem[] {
    return this.bundles.filter(
      (b) => this.selectedDistribution.has(b.distribution)
    ).filter(
      (b) => this.selectedTarget.has(b.target)
    ).filter(
      (b) => this.selectedState.has((b.readonly ? 'Readonly' : 'Editable'))
    ).filter(
      (b) => this.selectedCreator.has(b.creator)
    );
  }
}
